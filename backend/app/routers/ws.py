"""
WebSocket Detection Stream Router for SHADOW-NET.
Provides endpoint /ws/detection/{session_id} for streaming live audio chunks
and receiving continuous prediction events, spectrogram matrices, and alerts.
"""

import time
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db import get_db
from app.config import get_settings
from app.audio.preprocessing import load_audio, decode_base64_audio
from app.audio.vad import get_vad
from app.audio.features import slice_into_windows, extract_all_features
from app.ml.factory import get_detector
from app.ml.decision import DecisionEngine
from app.ml.explainer import explain_verdict
from app.models.incident import PredictionType, ThreatLevel
from app.services.ws_manager import ws_manager
from app.services.incident_service import handle_detection_trigger

logger = logging.getLogger("shadow_net.routers.ws")

router = APIRouter(tags=["WebSocket Real-Time"])


@router.websocket("/ws/detection/{session_id}")
async def detection_websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Live bidirectional WebSocket endpoint for streaming audio windows and
    receiving real-time predictions, spectrogram matrices, and incident alerts.
    """
    await ws_manager.connect(websocket, session_id)

    db = get_db()
    settings = get_settings()
    detector = get_detector()
    decision_engine = DecisionEngine(
        real_threshold=settings.REAL_THRESHOLD,
        deepfake_threshold=settings.DEEPFAKE_THRESHOLD,
    )

    model_status = getattr(detector, "model_status", "NOT_TRAINED")
    is_heuristic = getattr(detector, "is_heuristic_placeholder", True)
    model_version = getattr(detector, "version", "v1")

    # Send initial connection confirmation
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id,
        "mode": detector.mode,
        "model_name": detector.name,
        "model_version": model_version,
        "model_status": model_status,
        "is_heuristic_placeholder": is_heuristic,
        "real_threshold": settings.REAL_THRESHOLD,
        "deepfake_threshold": settings.DEEPFAKE_THRESHOLD,
        "timestamp": time.time(),
        "status": "ready",
    })

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format."})
                continue

            msg_type = msg.get("type", "audio_chunk")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
                continue

            if msg_type == "audio_chunk":
                audio_b64 = msg.get("audio_base64")
                if not audio_b64:
                    await websocket.send_json({"type": "error", "message": "Missing 'audio_base64' payload."})
                    continue

                start_t = time.perf_counter()

                try:
                    raw_bytes = decode_base64_audio(audio_b64)
                    audio, sr = load_audio(raw_bytes, target_sr=16000)
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Audio decode failed: {str(e)}"})
                    continue

                if audio.size == 0:
                    continue

                # Run VAD
                vad = get_vad()
                speech_audio, intervals, vad_meta = vad.filter_speech(audio, sr=sr)
                active_audio = speech_audio if speech_audio.size > 0 else audio

                # Windows
                windows = slice_into_windows(active_audio, sr=sr, window_sec=2.0, hop_sec=1.0)
                window_results = []
                sustained_counter = 0

                for w in windows:
                    feats = extract_all_features(w["audio"], sr=sr)
                    pred_res = detector.predict_window(
                        feats["mel_spectrogram"],
                        window_start=w["start_sec"],
                        window_end=w["end_sec"],
                    )
                    fake_prob = pred_res.get("ai_probability", pred_res["fake_probability"])
                    real_prob = pred_res.get("real_probability", 1.0 - fake_prob)

                    win_pred, win_threat, win_conf = decision_engine.evaluate_window(fake_prob)

                    if fake_prob >= settings.DEEPFAKE_THRESHOLD:
                        sustained_counter += 1
                    else:
                        sustained_counter = 0

                    is_sustained = (sustained_counter >= 2)

                    win_packet = {
                        "window_index": w["window_index"],
                        "start_sec": w["start_sec"],
                        "end_sec": w["end_sec"],
                        "fake_probability": fake_prob,
                        "ai_probability": fake_prob,
                        "real_probability": real_prob,
                        "prediction": win_pred.value,
                        "verdict": win_pred.value,
                        "confidence": win_conf,
                        "threat_level": win_threat.value,
                        "speaker_id": "Speaker 1",
                        "is_sustained_threat": is_sustained,
                        "visual_matrix": feats["visual_matrix"],
                    }
                    window_results.append(win_packet)

                # Overall session risk
                session_verdict = decision_engine.evaluate_session(
                    [{"fake_probability": wr["fake_probability"]} for wr in window_results],
                    model_status=model_status,
                )

                latency_ms = round((time.perf_counter() - start_t) * 1000, 2)

                # Generate acoustic feature explanation
                explanation_dict = {"top_reason": "Real-time acoustic analysis"}
                if window_results and feats:
                    try:
                        import numpy as _np
                        mel = feats.get("mel_spectrogram", _np.zeros((128, 1), dtype="float32"))
                        mfcc = feats.get("mfcc", _np.zeros((20, 1), dtype="float32"))
                        avg_fake_prob = session_verdict.get("average_fake_prob", session_verdict["confidence"])
                        exp_obj = explain_verdict(
                            mel_spectrogram=mel,
                            mfcc=mfcc,
                            fake_probability=avg_fake_prob,
                            verdict=session_verdict["prediction"].value,
                            confidence=session_verdict["confidence"],
                            mode=detector.mode,
                        )
                        explanation_dict = exp_obj.to_dict()
                    except Exception as _exp_err:
                        logger.warning(f"WebSocket explainer exception: {_exp_err}")

                out_packet = {
                    "type": "prediction_update",
                    "session_id": session_id,
                    "mode": detector.mode,
                    "model_name": detector.name,
                    "model_version": model_version,
                    "model_status": model_status,
                    "is_heuristic_placeholder": is_heuristic,
                    "prediction": session_verdict["prediction"].value,
                    "display_verdict": session_verdict.get("display_verdict", "UNCERTAIN (MODEL NOT TRAINED)"),
                    "confidence": session_verdict["confidence"],
                    "ai_probability": session_verdict.get("average_fake_prob", 0.5),
                    "real_probability": session_verdict.get("real_probability", round(1.0 - session_verdict.get("average_fake_prob", 0.5), 4)),
                    "threat_level": session_verdict["threat_level"].value,
                    "response_action": session_verdict["response_action"].value,
                    "latency_ms": latency_ms,
                    "sustained_threat_detected": session_verdict.get("sustained_threat_detected", False),
                    "windows": window_results,
                    "top_reason": explanation_dict.get("top_reason", ""),
                    "explanation": explanation_dict,
                    "timestamp": time.time(),
                }

                await websocket.send_json(out_packet)

                # Persist timeline event to db
                if db is not None:
                    import uuid as _uuid
                    import datetime as _dt
                    timeline_event = {
                        "event_id": str(_uuid.uuid4()),
                        "session_id": session_id,
                        "timestamp": _dt.datetime.utcnow(),
                        "prediction": session_verdict["prediction"].value,
                        "confidence": session_verdict["confidence"],
                        "fake_probability": session_verdict.get("average_fake_prob", 0.5),
                        "threat_level": session_verdict["threat_level"].value,
                        "response_action": session_verdict["response_action"].value,
                        "detection_latency_ms": latency_ms,
                        "num_windows": len(window_results),
                        "deepfake_window_count": session_verdict.get("deepfake_window_count", 0),
                        "top_reason": explanation_dict.get("top_reason", ""),
                        "mode": detector.mode,
                    }
                    try:
                        await db.analysis_timeline.insert_one(timeline_event)
                    except Exception as _e:
                        logger.warning(f"Failed to persist WS timeline event: {_e}")

                # If DEEPFAKE flagged, invoke automated incident response & session restriction
                if session_verdict["prediction"] == PredictionType.DEEPFAKE:
                    await handle_detection_trigger(
                        session_id=session_id,
                        prediction=session_verdict["prediction"],
                        confidence=session_verdict["confidence"],
                        threat_level=session_verdict["threat_level"],
                        detection_latency_ms=latency_ms,
                        trigger_details={"source": "websocket_stream", "windows_analyzed": len(windows)},
                        timeline=window_results,
                        db=db,
                    )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.warning(f"WebSocket error on session {session_id}: {e}")
        ws_manager.disconnect(websocket, session_id)

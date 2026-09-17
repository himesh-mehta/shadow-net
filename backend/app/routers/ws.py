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
from app.audio.preprocessing import load_audio, decode_base64_audio
from app.audio.vad import get_vad
from app.audio.features import slice_into_windows, extract_all_features
from app.ml.factory import get_detector
from app.ml.decision import DecisionEngine
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
    detector = get_detector()
    decision_engine = DecisionEngine(default_threshold=0.75)

    # Send initial connection confirmation
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id,
        "mode": detector.mode,
        "model_name": detector.name,
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

                for w in windows:
                    feats = extract_all_features(w["audio"], sr=sr)
                    pred_res = detector.predict_window(feats["mel_spectrogram"])
                    fake_prob = pred_res["fake_probability"]

                    win_pred, win_threat, win_conf = decision_engine.evaluate_window(fake_prob)

                    win_packet = {
                        "window_index": w["window_index"],
                        "start_sec": w["start_sec"],
                        "end_sec": w["end_sec"],
                        "fake_probability": fake_prob,
                        "prediction": win_pred.value,
                        "confidence": win_conf,
                        "threat_level": win_threat.value,
                        "visual_matrix": feats["visual_matrix"],
                    }
                    window_results.append(win_packet)

                # Overall session risk
                session_verdict = decision_engine.evaluate_session(
                    [{"fake_probability": wr["fake_probability"]} for wr in window_results]
                )

                latency_ms = round((time.perf_counter() - start_t) * 1000, 2)

                out_packet = {
                    "type": "prediction_update",
                    "session_id": session_id,
                    "mode": detector.mode,
                    "prediction": session_verdict["prediction"].value,
                    "confidence": session_verdict["confidence"],
                    "threat_level": session_verdict["threat_level"].value,
                    "response_action": session_verdict["response_action"].value,
                    "latency_ms": latency_ms,
                    "windows": window_results,
                    "timestamp": time.time(),
                }

                await websocket.send_json(out_packet)

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

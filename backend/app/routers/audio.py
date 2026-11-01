"""
Audio Analysis Router for SHADOW-NET.
Provides POST /audio/analyze supporting multipart WAV files and base64 audio chunks.
Executes:
1. Preprocessing (Mono, 16kHz, Amplitude Normalization)
2. Voice Activity Detection (drop silence)
3. Rolling Window Slicing (~1-2s)
4. Feature Extraction (Mel-Spectrogram & MFCC)
5. Model Inference (ResNet-18 or DemoFallbackDetector)
6. Decision Engine (REAL / DEEPFAKE / UNCERTAIN + Threat Level)
"""

import time
import json
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, status
from fastapi.responses import StreamingResponse

from app.db import get_db
from app.config import get_settings
from app.audio.preprocessing import load_audio, decode_base64_audio
from app.audio.vad import get_vad
from app.audio.features import slice_into_windows, extract_all_features
from app.ml.factory import get_detector
from app.ml.pretrained import DetectorUnavailable
from starlette.concurrency import run_in_threadpool
import numpy as np
from app.ml.decision import DecisionEngine
from app.ml.explainer import explain_verdict
from app.models.incident import PredictionType, ThreatLevel, ResponseAction

logger = logging.getLogger("shadow_net.routers.audio")

router = APIRouter(prefix="/audio", tags=["Audio Pipeline"])


class Base64AudioPayload(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio string (WAV or PCM)")
    session_id: Optional[str] = Field(None, description="Optional controlled test session ID")
    window_length: Optional[float] = Field(None, ge=0.5, le=5.0, description="Window duration in seconds")
    vad_sensitivity: Optional[int] = Field(None, ge=0, le=3, description="VAD sensitivity (0-3)")
    detection_threshold: Optional[float] = Field(None, ge=0.5, le=0.99, description="Custom detection threshold")


class WindowInferenceSummary(BaseModel):
    window_index: int
    start_sec: float
    end_sec: float
    fake_probability: float
    ai_probability: float = 0.50
    real_probability: float = 0.50
    prediction: PredictionType
    verdict: str = "UNCERTAIN"
    threat_level: ThreatLevel
    speaker_id: str = "Speaker 1"
    is_sustained_threat: bool = False
    is_padded: bool
    mel_shape: List[int]
    mfcc_shape: List[int]
    visual_matrix: List[List[float]]


class AudioAnalysisResponse(BaseModel):
    status: str = "success"
    session_id: Optional[str] = None
    mode: str = Field(..., description="'demo' (synthetic fallback) or 'ml' (production ResNet-18 inference)")
    model_name: str
    model_version: str = "v1"
    model_status: str = "NOT_TRAINED"
    is_heuristic_placeholder: bool = True
    display_verdict: str = "UNCERTAIN (MODEL NOT TRAINED)"
    validation_status: str = "NOT_LOCALLY_VALIDATED"
    score_type: str = "uncalibrated_softmax"
    is_synthetic: bool
    prediction: PredictionType
    confidence: float
    ai_probability: float = 0.50
    real_probability: float = 0.50
    threat_level: ThreatLevel
    response_action: ResponseAction
    detection_latency_ms: float
    sample_rate: int
    original_duration_sec: float
    speech_duration_sec: float
    dropped_silence_sec: float
    vad_engine: str
    num_windows: int
    deepfake_window_count: int
    sustained_threat_detected: bool = False
    windows: List[WindowInferenceSummary]
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Human-readable 'why' explanation: acoustic feature signals and plain-English reasoning",
    )


async def _process_audio_pipeline(
    audio_bytes: bytes,
    session_id: Optional[str] = None,
    window_length: Optional[float] = None,
    vad_sensitivity: Optional[int] = None,
    detection_threshold: Optional[float] = None,
    db=None,
) -> AudioAnalysisResponse:
    """Internal orchestration of preprocessing -> VAD -> windowing -> features -> ML inference -> decision engine."""
    start_time = time.perf_counter()

    # Read system settings from DB or defaults
    settings = get_settings()
    configured_demo = settings.DEMO_MODE
    configured_window = window_length or settings.AUDIO_WINDOW_SECONDS
    configured_vad = vad_sensitivity if vad_sensitivity is not None else settings.VAD_SENSITIVITY
    configured_threshold = detection_threshold or settings.DETECTION_THRESHOLD
    # Phase 1: two-threshold verdict scheme
    configured_real_th = settings.REAL_THRESHOLD
    configured_deepfake_th = settings.DEEPFAKE_THRESHOLD
    # If operator passed a legacy single threshold via API, derive symmetric bands from it
    if detection_threshold is not None:
        configured_real_th = round(1.0 - detection_threshold, 4)
        configured_deepfake_th = detection_threshold

    if db is not None:
        db_settings = await db.settings.find_one({"scope": "global"})
        if db_settings:
            configured_demo = db_settings.get("demo_mode", configured_demo)
            if window_length is None:
                configured_window = db_settings.get("audio_window_length", configured_window)
            if vad_sensitivity is None:
                configured_vad = db_settings.get("vad_sensitivity", configured_vad)
            if detection_threshold is None:
                configured_threshold = db_settings.get("detection_threshold", configured_threshold)
                if "detection_threshold" in db_settings:
                    configured_real_th = round(1.0 - configured_threshold, 4)
                    configured_deepfake_th = configured_threshold

    try:
        detector = await run_in_threadpool(get_detector, demo_mode=configured_demo)
    except DetectorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not 0.5 <= configured_window <= 5.0 or not 0.5 < configured_deepfake_th < 1:
        raise HTTPException(status_code=422, detail="Window must be 0.5–5s and detection threshold greater than 0.5.")

    # 1. Preprocessing: Decode, Mono-convert, Resample to 16kHz, Normalize
    try:
        audio, sr = load_audio(audio_bytes, target_sr=16000)
    except Exception as e:
        logger.error(f"Audio decoding/preprocessing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to decode or process audio: {str(e)}"
        )

    if audio.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided audio stream contains no decodable sample data."
        )

    if len(audio) < sr // 2 or len(audio) > settings.MAX_AUDIO_SECONDS * sr or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-6:
        raise HTTPException(status_code=422, detail="Provide 0.5–60 seconds of non-silent, finite audio.")

    # 2. Voice Activity Detection (drop silence)
    vad = get_vad()
    speech_audio, intervals, vad_meta = vad.filter_speech(
        audio, sr=sr, sensitivity=configured_vad
    )

    # If VAD dropped all frames as silence, fallback to original to permit analysis
    # Keep waveform timing intact for pretrained models; VAD is reported as telemetry only.
    active_audio = audio if getattr(detector, "uses_waveform", False) else (speech_audio if speech_audio.size > 0 else audio)

    # 3. Rolling Window Slicing (~1-2 seconds)
    windows = slice_into_windows(
        active_audio,
        sr=sr,
        window_sec=configured_window,
        hop_sec=configured_window * 0.5,
    )

    # 4. Feature Extraction & Model Inference per window
    decision_engine = DecisionEngine(
        real_threshold=configured_real_th,
        deepfake_threshold=configured_deepfake_th,
    )

    model_status = getattr(detector, "model_status", "NOT_TRAINED")
    window_summaries: List[WindowInferenceSummary] = []
    window_predictions_for_agg = []
    sustained_counter = 0

    for w in windows:
        feats = await run_in_threadpool(extract_all_features, w["audio"], sr=sr)
        mel_spectrogram = feats["mel_spectrogram"]

        # Run inference through active detector
        pred_result = await run_in_threadpool(detector.predict_audio,
            w["audio"][:round((w["end_sec"] - w["start_sec"]) * sr)], sr=sr,
            window_start=w["start_sec"],
            window_end=w["end_sec"],
        )
        fake_prob = pred_result.get("ai_probability", pred_result["fake_probability"])
        real_prob = pred_result.get("real_probability", 1.0 - fake_prob)

        # Evaluate window with Decision Engine
        win_pred, win_threat, win_conf = decision_engine.evaluate_window(
            fake_prob
        )

        if model_status != "TRAINED":
            win_pred, win_threat, win_conf = PredictionType.UNCERTAIN, ThreatLevel.MEDIUM, 0.5

        if model_status == "TRAINED" and fake_prob >= configured_deepfake_th:
            sustained_counter += 1
        else:
            sustained_counter = 0

        is_sustained = (sustained_counter >= 2)

        window_predictions_for_agg.append({
            "fake_probability": fake_prob,
            "ai_probability": fake_prob,
            "real_probability": real_prob,
            "prediction": win_pred,
            "threat_level": win_threat,
            "confidence": win_conf,
        })

        window_summaries.append(
            WindowInferenceSummary(
                window_index=w["window_index"],
                start_sec=w["start_sec"],
                end_sec=w["end_sec"],
                fake_probability=fake_prob,
                ai_probability=fake_prob,
                real_probability=real_prob,
                prediction=win_pred,
                verdict=win_pred.value,
                threat_level=win_threat,
                speaker_id="Speaker 1",
                is_sustained_threat=is_sustained,
                is_padded=w["is_padded"],
                mel_shape=feats["mel_shape"],
                mfcc_shape=feats["mfcc_shape"],
                visual_matrix=feats["visual_matrix"],
            )
        )

    # 5. Overall Session Decision & Risk Evaluation
    model_status = getattr(detector, "model_status", "NOT_TRAINED")
    session_verdict = decision_engine.evaluate_session(
        window_predictions_for_agg,
        model_status=model_status,
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 6. Generate human-readable explanation from the best window features
    best_window_feats = None
    best_window_mfcc = None
    if window_predictions_for_agg:
        agg_prob = session_verdict["average_fake_prob"]
        best_idx = min(
            range(len(window_predictions_for_agg)),
            key=lambda i: abs(window_predictions_for_agg[i]["fake_probability"] - agg_prob),
        )
        try:
            rep_window = windows[best_idx]
            rep_feats = extract_all_features(rep_window["audio"], sr=sr)
            best_window_feats = rep_feats["mel_spectrogram"]
            best_window_mfcc = rep_feats["mfcc"]
        except Exception:
            pass

    import numpy as _np
    explanation = explain_verdict(
        mel_spectrogram=best_window_feats if best_window_feats is not None else _np.zeros((128, 1), dtype="float32"),
        mfcc=best_window_mfcc if best_window_mfcc is not None else _np.zeros((20, 1), dtype="float32"),
        fake_probability=session_verdict["average_fake_prob"],
        verdict=session_verdict["prediction"].value,
        confidence=session_verdict["confidence"],
        mode=detector.mode,
    ).to_dict()

    # 7. Persist analysis timeline event (lightweight, no raw audio)
    if session_id and db is not None:
        import uuid as _uuid
        timeline_event = {
            "event_id": str(_uuid.uuid4()),
            "session_id": session_id,
            "timestamp": __import__("datetime").datetime.utcnow(),
            "prediction": session_verdict["prediction"].value,
            "confidence": session_verdict["confidence"],
            "fake_probability": session_verdict["average_fake_prob"],
            "threat_level": session_verdict["threat_level"].value,
            "response_action": session_verdict["response_action"].value,
            "detection_latency_ms": elapsed_ms,
            "num_windows": len(window_summaries),
            "deepfake_window_count": session_verdict["deepfake_window_count"],
            "sustained_threat_detected": session_verdict.get("sustained_threat_detected", False),
            "top_reason": explanation.get("top_reason"),
            "mode": detector.mode,
            "model_status": model_status,
        }
        try:
            await db.analysis_timeline.insert_one(timeline_event)
        except Exception as _e:
            logger.warning(f"Failed to persist timeline event: {_e}")

    # 8. Automated Incident Response if session_id is provided and deepfake detected
    if session_id and session_verdict["prediction"] in (PredictionType.DEEPFAKE, PredictionType.AI_SUSPECTED):
        from app.services.incident_service import handle_detection_trigger
        await handle_detection_trigger(
            session_id=session_id,
            prediction=session_verdict["prediction"],
            confidence=session_verdict["confidence"],
            threat_level=session_verdict["threat_level"],
            detection_latency_ms=elapsed_ms,
            trigger_details={"source": "audio_analyze_endpoint", "windows_count": len(window_summaries)},
            timeline=[w.dict() for w in window_summaries],
            db=db,
        )

    return AudioAnalysisResponse(
        status="success",
        session_id=session_id,
        mode=detector.mode,
        model_name=detector.name,
        model_version=getattr(detector, "version", "v1"),
        model_status=model_status,
        is_heuristic_placeholder=getattr(detector, "is_heuristic_placeholder", True),
        display_verdict=session_verdict.get("display_verdict", "UNCERTAIN (MODEL NOT TRAINED)"),
        validation_status=getattr(detector, "validation_status", "NOT_LOCALLY_VALIDATED"),
        score_type="uncalibrated_softmax" if detector.is_loaded else "demo_placeholder",
        is_synthetic=getattr(detector, "is_heuristic_placeholder", True),
        prediction=session_verdict["prediction"],
        confidence=session_verdict["confidence"],
        ai_probability=session_verdict["ai_probability"],
        real_probability=session_verdict.get("real_probability", round(1.0 - session_verdict["average_fake_prob"], 4)),
        threat_level=session_verdict["threat_level"],
        response_action=session_verdict["response_action"],
        detection_latency_ms=elapsed_ms,
        sample_rate=sr,
        original_duration_sec=vad_meta["original_duration"],
        speech_duration_sec=vad_meta["speech_duration"],
        dropped_silence_sec=vad_meta["dropped_duration"],
        vad_engine=vad_meta.get("vad_engine", "VAD"),
        num_windows=len(window_summaries),
        deepfake_window_count=session_verdict["deepfake_window_count"],
        sustained_threat_detected=session_verdict.get("sustained_threat_detected", False),
        windows=window_summaries,
        explanation=explanation,
    )


@router.post("/analyze", response_model=AudioAnalysisResponse)
async def analyze_audio(
    file: Optional[UploadFile] = File(None, description="Multipart WAV/audio file"),
    audio_base64: Optional[str] = Form(None, description="Base64 encoded audio string"),
    session_id: Optional[str] = Form(None, description="Optional controlled test session ID"),
    window_length: Optional[float] = Form(None, description="Window length in seconds"),
    vad_sensitivity: Optional[int] = Form(None, description="VAD sensitivity (0-3)"),
    detection_threshold: Optional[float] = Form(None, description="Custom detection threshold"),
    db=Depends(get_db),
):
    """
    Analyzes an audio stream (multipart file or base64) with the full ML detection pipeline.
    Returns three-state prediction (REAL / DEEPFAKE / UNCERTAIN), confidence, threat level,
    measured latency, and operational mode ('demo' or 'ml').
    """
    if file is not None:
        audio_bytes = await file.read()
    elif audio_base64 is not None:
        audio_bytes = decode_base64_audio(audio_base64)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either a multipart audio 'file' or 'audio_base64' string."
        )

    return await _process_audio_pipeline(
        audio_bytes=audio_bytes,
        session_id=session_id,
        window_length=window_length,
        vad_sensitivity=vad_sensitivity,
        detection_threshold=detection_threshold,
        db=db,
    )


@router.post("/analyze/json", response_model=AudioAnalysisResponse)
async def analyze_audio_json(
    payload: Base64AudioPayload,
    db=Depends(get_db),
):
    """
    JSON endpoint for base64 audio chunks (convenient for WebSocket streaming or client libraries).
    """
    audio_bytes = decode_base64_audio(payload.audio_base64)

    return await _process_audio_pipeline(
        audio_bytes=audio_bytes,
        session_id=payload.session_id,
        window_length=payload.window_length,
        vad_sensitivity=payload.vad_sensitivity,
        detection_threshold=payload.detection_threshold,
        db=db,
    )


# ──────────────────────────────────────────────────────────────────────────────
# SSE Streaming Endpoint — emits one event per window, then a final verdict
# ──────────────────────────────────────────────────────────────────────────────

async def _stream_audio_pipeline(
    audio_bytes: bytes,
    session_id: Optional[str] = None,
    window_length: Optional[float] = None,
    vad_sensitivity: Optional[int] = None,
    detection_threshold: Optional[float] = None,
    db=None,
) -> AsyncGenerator[str, None]:
    """
    Core SSE generator: preprocesses audio, runs VAD, slices into windows,
    and yields a Server-Sent Event JSON string per window as inference completes.
    Final event carries the full session verdict and explanation.

    SSE format (each yield):  data: <json>\n\n
    Event types:
      - 'pipeline_start'   : meta + total window count
      - 'window'           : per-segment result with start_sec, end_sec, prediction
      - 'session_verdict'  : aggregated result + explanation
      - 'error'            : exception message
    """
    import numpy as _np
    import uuid as _uuid
    import datetime as _dt

    def sse(event_type: str, payload: dict) -> str:
        payload["type"] = event_type
        return f"data: {json.dumps(payload)}\n\n"

    settings = get_settings()
    configured_demo = settings.DEMO_MODE
    configured_window = window_length or settings.AUDIO_WINDOW_SECONDS
    configured_vad = vad_sensitivity if vad_sensitivity is not None else settings.VAD_SENSITIVITY
    configured_real_th = settings.REAL_THRESHOLD
    configured_deepfake_th = settings.DEEPFAKE_THRESHOLD
    configured_threshold = detection_threshold or settings.DETECTION_THRESHOLD

    if detection_threshold is not None:
        configured_real_th = round(1.0 - detection_threshold, 4)
        configured_deepfake_th = detection_threshold

    if db is not None:
        db_settings = await db.settings.find_one({"scope": "global"})
        if db_settings:
            configured_demo = db_settings.get("demo_mode", configured_demo)
            if window_length is None:
                configured_window = db_settings.get("audio_window_length", configured_window)
            if vad_sensitivity is None:
                configured_vad = db_settings.get("vad_sensitivity", configured_vad)
            if detection_threshold is None and "detection_threshold" in db_settings:
                configured_threshold = db_settings["detection_threshold"]
                configured_real_th = round(1.0 - configured_threshold, 4)
                configured_deepfake_th = configured_threshold

    try:
        detector = await run_in_threadpool(get_detector, demo_mode=configured_demo)
    except DetectorUnavailable as exc:
        yield sse("error", {"message": str(exc)})
        return
    if not 0.5 <= configured_window <= 5.0 or not 0.5 < configured_deepfake_th < 1:
        yield sse("error", {"message": "Window must be 0.5–5s and threshold greater than 0.5."})
        return

    # ── Preprocess ────────────────────────────────────────────────────────────
    try:
        audio, sr = load_audio(audio_bytes, target_sr=16000)
    except Exception as e:
        yield sse("error", {"message": f"Audio decode failed: {e}"})
        return

    if audio.size == 0:
        yield sse("error", {"message": "No decodable audio data found in the file."})
        return

    if len(audio) < sr // 2 or len(audio) > settings.MAX_AUDIO_SECONDS * sr or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-6:
        yield sse("error", {"message": "Provide 0.5–60 seconds of non-silent, finite audio."})
        return

    # ── VAD ───────────────────────────────────────────────────────────────────
    vad = get_vad()
    speech_audio, intervals, vad_meta = vad.filter_speech(audio, sr=sr, sensitivity=configured_vad)
    # Keep waveform timing intact for pretrained models; VAD is reported as telemetry only.
    active_audio = audio if getattr(detector, "uses_waveform", False) else (speech_audio if speech_audio.size > 0 else audio)

    # ── Window slicing ────────────────────────────────────────────────────────
    windows = slice_into_windows(
        active_audio, sr=sr,
        window_sec=configured_window,
        hop_sec=configured_window * 0.5,
    )

    if not windows:
        yield sse("error", {"message": "No audio windows could be extracted (audio too short?)"})
        return

    decision_engine = DecisionEngine(
        real_threshold=configured_real_th,
        deepfake_threshold=configured_deepfake_th,
    )

    total_duration = vad_meta.get("original_duration", 0.0)

    # ── Emit pipeline start ───────────────────────────────────────────────────
    model_status = getattr(detector, "model_status", "NOT_TRAINED")
    yield sse("pipeline_start", {
        "total_windows": len(windows),
        "window_sec": configured_window,
        "original_duration_sec": total_duration,
        "speech_duration_sec": vad_meta.get("speech_duration", 0.0),
        "sample_rate": sr,
        "mode": detector.mode,
        "model_name": detector.name,
        "model_version": getattr(detector, "version", "v1"),
        "model_status": model_status,
        "is_heuristic_placeholder": getattr(detector, "is_heuristic_placeholder", True),
        "session_id": session_id,
    })

    stream_window_packets = []
    # ── Per-window inference ──────────────────────────────────────────────────
    window_predictions_for_agg = []
    start_t = time.perf_counter()
    rep_feats_mel = None
    rep_feats_mfcc = None
    sustained_counter = 0

    for w in windows:
        feats = await run_in_threadpool(extract_all_features, w["audio"], sr=sr)
        pred_result = await run_in_threadpool(detector.predict_audio,
            w["audio"][:round((w["end_sec"] - w["start_sec"]) * sr)], sr=sr,
            window_start=w["start_sec"],
            window_end=w["end_sec"],
        )
        fake_prob = pred_result.get("ai_probability", pred_result["fake_probability"])
        real_prob = pred_result.get("real_probability", 1.0 - fake_prob)

        win_pred, win_threat, win_conf = decision_engine.evaluate_window(fake_prob)

        if model_status != "TRAINED":
            win_pred, win_threat, win_conf = PredictionType.UNCERTAIN, ThreatLevel.MEDIUM, 0.5

        if model_status == "TRAINED" and fake_prob >= configured_deepfake_th:
            sustained_counter += 1
        else:
            sustained_counter = 0

        is_sustained = (sustained_counter >= 2)

        window_predictions_for_agg.append({
            "fake_probability": fake_prob,
            "ai_probability": fake_prob,
            "real_probability": real_prob,
        })

        # Keep the window closest to 50% fake_prob for explanation later
        if rep_feats_mel is None or abs(fake_prob - 0.5) < abs(
            float(_np.mean(rep_feats_mel)) - 0.5
        ):
            rep_feats_mel = feats["mel_spectrogram"]
            rep_feats_mfcc = feats["mfcc"]

        window_event = {
            "window_index": w["window_index"],
            "start_sec": w["start_sec"],
            "end_sec": w["end_sec"],
            "fake_probability": round(fake_prob, 4),
            "ai_probability": round(fake_prob, 4),
            "real_probability": round(real_prob, 4),
            "prediction": win_pred.value,
            "verdict": win_pred.value,
            "threat_level": win_threat.value,
            "confidence": round(win_conf, 4),
            "speaker_id": "Speaker 1",
            "is_sustained_threat": is_sustained,
            "is_padded": w["is_padded"],
            "visual_matrix": feats["visual_matrix"],
        }
        stream_window_packets.append(window_event)
        yield sse("window", window_event)

    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

    # ── Session verdict ───────────────────────────────────────────────────────
    session_verdict = decision_engine.evaluate_session(
        window_predictions_for_agg,
        model_status=model_status,
    )

    explanation = explain_verdict(
        mel_spectrogram=rep_feats_mel if rep_feats_mel is not None else _np.zeros((128, 1), dtype="float32"),
        mfcc=rep_feats_mfcc if rep_feats_mfcc is not None else _np.zeros((20, 1), dtype="float32"),
        fake_probability=session_verdict["average_fake_prob"],
        verdict=session_verdict["prediction"].value,
        confidence=session_verdict["confidence"],
        mode=detector.mode,
    ).to_dict()

    # Persist timeline event
    if session_id and db is not None:
        try:
            await db.analysis_timeline.insert_one({
                "event_id": str(_uuid.uuid4()),
                "session_id": session_id,
                "timestamp": _dt.datetime.utcnow(),
                "prediction": session_verdict["prediction"].value,
                "confidence": session_verdict["confidence"],
                "fake_probability": session_verdict["average_fake_prob"],
                "threat_level": session_verdict["threat_level"].value,
                "response_action": session_verdict["response_action"].value,
                "detection_latency_ms": elapsed_ms,
                "num_windows": len(windows),
                "deepfake_window_count": session_verdict["deepfake_window_count"],
                "sustained_threat_detected": session_verdict.get("sustained_threat_detected", False),
                "top_reason": explanation.get("top_reason"),
                "mode": detector.mode,
                "model_status": model_status,
                "source": "stream",
            })
        except Exception as _e:
            logger.warning(f"SSE timeline persist failed: {_e}")

    if session_id and session_verdict["prediction"] in (PredictionType.DEEPFAKE, PredictionType.AI_SUSPECTED):
        from app.services.incident_service import handle_detection_trigger
        await handle_detection_trigger(
            session_id=session_id, prediction=session_verdict["prediction"],
            confidence=session_verdict["confidence"], threat_level=session_verdict["threat_level"],
            detection_latency_ms=elapsed_ms, trigger_details={"source": "wav_upload_stream", "model_name": detector.name},
            timeline=stream_window_packets, db=db,
        )

    yield sse("session_verdict", {
        "validation_status": getattr(detector, "validation_status", "NOT_LOCALLY_VALIDATED"),
        "score_type": "uncalibrated_softmax" if detector.is_loaded else "demo_placeholder",
        "prediction": session_verdict["prediction"].value,
        "display_verdict": session_verdict.get("display_verdict", "UNCERTAIN (MODEL NOT TRAINED)"),
        "confidence": session_verdict["confidence"],
        "threat_level": session_verdict["threat_level"].value,
        "response_action": session_verdict["response_action"].value,
        "average_fake_prob": session_verdict["average_fake_prob"],
        "ai_probability": session_verdict["ai_probability"],
        "real_probability": session_verdict.get("real_probability", round(1.0 - session_verdict["average_fake_prob"], 4)),
        "max_fake_prob": session_verdict["max_fake_prob"],
        "deepfake_window_count": session_verdict["deepfake_window_count"],
        "sustained_threat_detected": session_verdict.get("sustained_threat_detected", False),
        "total_windows": session_verdict["total_windows"],
        "detection_latency_ms": elapsed_ms,
        "original_duration_sec": total_duration,
        "speech_duration_sec": vad_meta.get("speech_duration", 0.0),
        "dropped_silence_sec": vad_meta.get("dropped_duration", 0.0),
        "mode": detector.mode,
        "model_name": detector.name,
        "model_version": getattr(detector, "version", "v1"),
        "model_status": model_status,
        "is_heuristic_placeholder": getattr(detector, "is_heuristic_placeholder", True),
        "session_id": session_id,
        "explanation": explanation,
    })


@router.post(
    "/analyze/stream",
    summary="Stream per-segment analysis via Server-Sent Events",
    description=(
        "Processes an audio file and streams per-window inference results as SSE events. "
        "The client receives a 'window' event for each audio segment as it's analysed, "
        "followed by a final 'session_verdict' event with the aggregated verdict and explanation."
    ),
    response_class=StreamingResponse,
)
async def analyze_audio_stream(
    file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    window_length: Optional[float] = Form(None),
    vad_sensitivity: Optional[int] = Form(None),
    detection_threshold: Optional[float] = Form(None),
    db=Depends(get_db),
):
    """
    SSE streaming endpoint for segment-level audio analysis.
    Returns Content-Type: text/event-stream.
    """
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide a multipart audio 'file' for the streaming endpoint."
        )

    audio_bytes = await file.read()

    return StreamingResponse(
        _safe_stream_audio_pipeline(
            audio_bytes=audio_bytes,
            session_id=session_id,
            window_length=window_length,
            vad_sensitivity=vad_sensitivity,
            detection_threshold=detection_threshold,
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        },
    )


async def _safe_stream_audio_pipeline(**kwargs):
    try:
        async for event in _stream_audio_pipeline(**kwargs):
            yield event
    except Exception as exc:
        logger.exception("Streaming audio analysis failed")
        yield "data: " + json.dumps({"type": "error", "message": str(exc)}) + "\n\n"

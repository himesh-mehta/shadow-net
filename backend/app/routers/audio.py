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
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, status

from app.db import get_db
from app.config import get_settings
from app.audio.preprocessing import load_audio, decode_base64_audio
from app.audio.vad import get_vad
from app.audio.features import slice_into_windows, extract_all_features
from app.ml.factory import get_detector
from app.ml.decision import DecisionEngine
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
    prediction: PredictionType
    threat_level: ThreatLevel
    is_padded: bool
    mel_shape: List[int]
    mfcc_shape: List[int]
    visual_matrix: List[List[float]]


class AudioAnalysisResponse(BaseModel):
    status: str = "success"
    session_id: Optional[str] = None
    mode: str = Field(..., description="'demo' (synthetic fallback) or 'ml' (production ResNet-18 inference)")
    model_name: str
    is_synthetic: bool
    prediction: PredictionType
    confidence: float
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
    windows: List[WindowInferenceSummary]


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
    configured_window = window_length or settings.AUDIO_WINDOW_SECONDS
    configured_vad = vad_sensitivity if vad_sensitivity is not None else settings.VAD_SENSITIVITY
    configured_threshold = detection_threshold or settings.DETECTION_THRESHOLD

    if db is not None:
        db_settings = await db.settings.find_one({"scope": "global"})
        if db_settings:
            if window_length is None:
                configured_window = db_settings.get("audio_window_length", configured_window)
            if vad_sensitivity is None:
                configured_vad = db_settings.get("vad_sensitivity", configured_vad)
            if detection_threshold is None:
                configured_threshold = db_settings.get("detection_threshold", configured_threshold)

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

    # 2. Voice Activity Detection (drop silence)
    vad = get_vad()
    speech_audio, intervals, vad_meta = vad.filter_speech(
        audio, sr=sr, sensitivity=configured_vad
    )

    # If VAD dropped all frames as silence, fallback to original to permit analysis
    active_audio = speech_audio if speech_audio.size > 0 else audio

    # 3. Rolling Window Slicing (~1-2 seconds)
    windows = slice_into_windows(
        active_audio,
        sr=sr,
        window_sec=configured_window,
        hop_sec=configured_window * 0.5,
    )

    # 4. Feature Extraction & Model Inference per window
    detector = get_detector()
    decision_engine = DecisionEngine(default_threshold=configured_threshold)

    window_summaries: List[WindowInferenceSummary] = []
    window_predictions_for_agg = []

    for w in windows:
        feats = extract_all_features(w["audio"], sr=sr)
        mel_spectrogram = feats["mel_spectrogram"]

        # Run inference through active detector (ResNet-18 or Demo fallback)
        pred_result = detector.predict_window(mel_spectrogram)
        fake_prob = pred_result["fake_probability"]

        # Evaluate window with Decision Engine
        win_pred, win_threat, win_conf = decision_engine.evaluate_window(
            fake_prob, threshold=configured_threshold
        )

        window_predictions_for_agg.append({
            "fake_probability": fake_prob,
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
                prediction=win_pred,
                threat_level=win_threat,
                is_padded=w["is_padded"],
                mel_shape=feats["mel_shape"],
                mfcc_shape=feats["mfcc_shape"],
                visual_matrix=feats["visual_matrix"],
            )
        )

    # 5. Overall Session Decision & Risk Evaluation
    session_verdict = decision_engine.evaluate_session(
        window_predictions_for_agg, threshold=configured_threshold
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return AudioAnalysisResponse(
        status="success",
        session_id=session_id,
        mode=detector.mode,
        model_name=detector.name,
        is_synthetic=(detector.mode == "demo"),
        prediction=session_verdict["prediction"],
        confidence=session_verdict["confidence"],
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
        windows=window_summaries,
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

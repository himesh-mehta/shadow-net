"""
Audio Analysis Router for SHADOW-NET.
Provides POST /audio/analyze supporting:
1. Multipart WAV file upload
2. Base64 encoded audio chunks

Executes full preprocessing, VAD silence dropping, rolling window slicing,
and feature extraction (Mel-Spectrogram & MFCC).
"""

import time
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, status

from app.db import get_db
from app.config import get_settings
from app.audio.preprocessing import load_audio
from app.audio.vad import get_vad
from app.audio.features import slice_into_windows, extract_all_features

logger = logging.getLogger("shadow_net.routers.audio")

router = APIRouter(prefix="/audio", tags=["Audio Pipeline"])


class Base64AudioPayload(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio string (WAV or PCM)")
    session_id: Optional[str] = Field(None, description="Optional controlled test session ID")
    window_length: Optional[float] = Field(None, ge=0.5, le=5.0, description="Window duration in seconds")
    vad_sensitivity: Optional[int] = Field(None, ge=0, le=3, description="VAD sensitivity (0-3)")


class WindowFeatureSummary(BaseModel):
    window_index: int
    start_sec: float
    end_sec: float
    is_padded: bool
    mel_shape: List[int]
    mfcc_shape: List[int]
    visual_matrix: List[List[float]]


class AudioAnalysisResponse(BaseModel):
    status: str = "success"
    session_id: Optional[str] = None
    processing_latency_ms: float
    sample_rate: int
    original_duration_sec: float
    speech_duration_sec: float
    dropped_silence_sec: float
    vad_engine: str
    num_windows: int
    windows: List[WindowFeatureSummary]


async def _process_audio_pipeline(
    audio_bytes: bytes,
    session_id: Optional[str] = None,
    window_length: Optional[float] = None,
    vad_sensitivity: Optional[int] = None,
    db=None,
) -> AudioAnalysisResponse:
    """Internal orchestration of preprocessing -> VAD -> windowing -> feature extraction."""
    start_time = time.perf_counter()

    # Read system settings from DB or defaults
    settings = get_settings()
    configured_window = window_length or settings.AUDIO_WINDOW_SECONDS
    configured_vad = vad_sensitivity if vad_sensitivity is not None else settings.VAD_SENSITIVITY

    if db is not None:
        db_settings = await db.settings.find_one({"scope": "global"})
        if db_settings:
            if window_length is None:
                configured_window = db_settings.get("audio_window_length", configured_window)
            if vad_sensitivity is None:
                configured_vad = db_settings.get("vad_sensitivity", configured_vad)

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

    # If VAD dropped all frames as silence, fallback to original to allow analysis
    active_audio = speech_audio if speech_audio.size > 0 else audio

    # 3. Rolling Window Slicing (~1-2 seconds)
    windows = slice_into_windows(
        active_audio,
        sr=sr,
        window_sec=configured_window,
        hop_sec=configured_window * 0.5,
    )

    # 4. Feature Extraction per window (MFCC & Mel-Spectrogram)
    window_summaries = []
    for w in windows:
        feats = extract_all_features(w["audio"], sr=sr)
        window_summaries.append(
            WindowFeatureSummary(
                window_index=w["window_index"],
                start_sec=w["start_sec"],
                end_sec=w["end_sec"],
                is_padded=w["is_padded"],
                mel_shape=feats["mel_shape"],
                mfcc_shape=feats["mfcc_shape"],
                visual_matrix=feats["visual_matrix"],
            )
        )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return AudioAnalysisResponse(
        status="success",
        session_id=session_id,
        processing_latency_ms=elapsed_ms,
        sample_rate=sr,
        original_duration_sec=vad_meta["original_duration"],
        speech_duration_sec=vad_meta["speech_duration"],
        dropped_silence_sec=vad_meta["dropped_duration"],
        vad_engine=vad_meta.get("vad_engine", "VAD"),
        num_windows=len(window_summaries),
        windows=window_summaries,
    )


@router.post("/analyze", response_model=AudioAnalysisResponse)
async def analyze_audio(
    file: Optional[UploadFile] = File(None, description="Multipart WAV/audio file"),
    audio_base64: Optional[str] = Form(None, description="Base64 encoded audio string"),
    session_id: Optional[str] = Form(None, description="Optional controlled test session ID"),
    window_length: Optional[float] = Form(None, description="Window length in seconds"),
    vad_sensitivity: Optional[int] = Form(None, description="VAD sensitivity (0-3)"),
    db=Depends(get_db),
):
    """
    Primary audio analysis endpoint accepting multipart file upload or form-encoded base64.
    """
    if file is not None:
        audio_bytes = await file.read()
    elif audio_base64 is not None:
        from app.audio.preprocessing import decode_base64_audio
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
        db=db,
    )


@router.post("/analyze/json", response_model=AudioAnalysisResponse)
async def analyze_audio_json(
    payload: Base64AudioPayload,
    db=Depends(get_db),
):
    """
    JSON endpoint for base64 audio chunks (convenient for WebSocket fallback or client libraries).
    """
    from app.audio.preprocessing import decode_base64_audio
    audio_bytes = decode_base64_audio(payload.audio_base64)

    return await _process_audio_pipeline(
        audio_bytes=audio_bytes,
        session_id=payload.session_id,
        window_length=payload.window_length,
        vad_sensitivity=payload.vad_sensitivity,
        db=db,
    )

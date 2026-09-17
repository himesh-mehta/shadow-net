"""
Audio Preprocessing Module for SHADOW-NET.
Handles decoding (binary and base64), mono-conversion, resampling (16kHz),
and amplitude normalization.
"""

import base64
import io
import logging
from typing import Tuple, Union
import numpy as np
import soundfile as sf
import librosa

logger = logging.getLogger("shadow_net.audio.preprocessing")

TARGET_SAMPLE_RATE = 16000


def decode_base64_audio(b64_string: str) -> bytes:
    """
    Decodes a base64 encoded audio string, stripping optional data URI scheme.
    """
    if "," in b64_string:
        # Strip header like 'data:audio/wav;base64,...'
        b64_string = b64_string.split(",", 1)[1]
    return base64.b64decode(b64_string)


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    Normalizes audio waveform amplitude to [-1.0, 1.0] range.
    Safely handles pure silence/near-zero arrays.
    """
    if audio.size == 0:
        return audio

    peak = np.max(np.abs(audio))
    if peak > 1e-6:
        return (audio / peak).astype(np.float32)
    return audio.astype(np.float32)


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    """
    Resamples audio to the target sampling rate (16,000 Hz) using librosa.
    """
    if orig_sr == target_sr:
        return audio.astype(np.float32)
    return librosa.resample(y=audio, orig_sr=orig_sr, target_sr=target_sr).astype(np.float32)


def load_audio(
    source: Union[bytes, str, io.BytesIO],
    target_sr: int = TARGET_SAMPLE_RATE,
) -> Tuple[np.ndarray, int]:
    """
    Loads audio from raw bytes, base64 string, or BytesIO buffer.
    Converts to mono, resamples to target_sr (16kHz), and normalizes amplitude.

    Returns:
        Tuple[np.ndarray, int]: (preprocessed_mono_waveform, sample_rate)
    """
    if isinstance(source, str):
        # Could be base64 string or file path
        if source.startswith("data:audio") or len(source) > 256 and not source.endswith(".wav"):
            raw_bytes = decode_base64_audio(source)
            bio = io.BytesIO(raw_bytes)
        else:
            bio = source
    elif isinstance(source, bytes):
        bio = io.BytesIO(source)
    else:
        bio = source

    # Read audio via soundfile
    try:
        data, sr = sf.read(bio, dtype="float32")
    except Exception as e:
        logger.error(f"soundfile failed to read audio stream: {e}")
        # Fallback to librosa.load
        if isinstance(bio, io.BytesIO):
            bio.seek(0)
        data, sr = librosa.load(bio, sr=None, mono=False)

    # 1. Multi-channel / Stereo to Mono
    if data.ndim > 1:
        if data.shape[0] < data.shape[1]:  # Shape is (channels, samples)
            data = np.mean(data, axis=0)
        else:  # Shape is (samples, channels)
            data = np.mean(data, axis=1)

    # 2. Resample to target rate (16kHz)
    if sr != target_sr:
        data = resample_audio(data, orig_sr=sr, target_sr=target_sr)
        sr = target_sr

    # 3. Normalize amplitude
    data = normalize_audio(data)

    return data, sr

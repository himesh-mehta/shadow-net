"""
Acoustic Feature Extraction Module for SHADOW-NET.
Computes:
1. Rolling window slicing (~1-2 seconds)
2. Log Mel-Spectrograms (n_mels=128)
3. MFCCs (n_mfcc=20)
4. Visual representation matrices and base64 heatmap representations for frontend
"""

import io
import math
from typing import List, Dict, Any, Tuple
import numpy as np
import librosa

TARGET_SR = 16000
DEFAULT_WINDOW_SEC = 2.0
DEFAULT_HOP_SEC = 1.0
DEFAULT_N_MELS = 128
DEFAULT_N_MFCC = 20
DEFAULT_N_FFT = 1024
DEFAULT_HOP_LENGTH = 512


def slice_into_windows(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    window_sec: float = DEFAULT_WINDOW_SEC,
    hop_sec: float = DEFAULT_HOP_SEC,
) -> List[Dict[str, Any]]:
    """
    Slices preprocessed speech audio into rolling windows of specified duration.

    Args:
        audio: 1D normalized float32 waveform.
        sr: Audio sample rate (16000).
        window_sec: Window length in seconds (default 2.0).
        hop_sec: Stride length in seconds (default 1.0 for 50% overlap).

    Returns:
        List of dicts containing window_index, start_sec, end_sec, and audio slice.
    """
    if audio.size == 0:
        return []

    window_samples = int(window_sec * sr)
    hop_samples = int(hop_sec * sr)
    total_samples = len(audio)

    # If audio is shorter than a single window, pad it to window_samples
    if total_samples < window_samples:
        padded = np.zeros(window_samples, dtype=np.float32)
        padded[:total_samples] = audio
        return [
            {
                "window_index": 0,
                "start_sec": 0.0,
                "end_sec": round(float(total_samples / sr), 3),
                "audio": padded,
                "is_padded": True,
            }
        ]

    windows = []
    start = 0
    idx = 0

    while start + window_samples <= total_samples:
        chunk = audio[start : start + window_samples]
        windows.append(
            {
                "window_index": idx,
                "start_sec": round(float(start / sr), 3),
                "end_sec": round(float((start + window_samples) / sr), 3),
                "audio": chunk,
                "is_padded": False,
            }
        )
        start += hop_samples
        idx += 1

    # If there is remaining speech longer than 0.5s that wasn't included
    remaining = total_samples - start
    if remaining >= int(0.5 * sr) and start < total_samples:
        tail = np.zeros(window_samples, dtype=np.float32)
        tail[:remaining] = audio[start:total_samples]
        windows.append(
            {
                "window_index": idx,
                "start_sec": round(float(start / sr), 3),
                "end_sec": round(float(total_samples / sr), 3),
                "audio": tail,
                "is_padded": True,
            }
        )

    return windows


def extract_mel_spectrogram(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    n_mels: int = DEFAULT_N_MELS,
    n_fft: int = DEFAULT_N_FFT,
    hop_length: int = DEFAULT_HOP_LENGTH,
) -> np.ndarray:
    """
    Generates log Mel-Spectrogram in dB scale.
    Output shape: (n_mels, time_frames).
    """
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_mels=n_mels,
        n_fft=n_fft,
        hop_length=hop_length,
        fmax=sr // 2,
    )
    # Convert power to decibels (log scale)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    return mel_db.astype(np.float32)


def extract_mfcc(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    n_mfcc: int = DEFAULT_N_MFCC,
    n_mels: int = DEFAULT_N_MELS,
) -> np.ndarray:
    """
    Extracts Mel-Frequency Cepstral Coefficients (MFCCs).
    Output shape: (n_mfcc, time_frames).
    """
    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sr,
        n_mfcc=n_mfcc,
        n_mels=n_mels,
    )
    return mfcc.astype(np.float32)


def render_spectrogram_to_matrix(
    mel_db: np.ndarray,
    target_freq_bins: int = 16,
    target_time_steps: int = 32,
) -> List[List[float]]:
    """
    Downsamples and normalizes a Mel-spectrogram to a compact 2D float matrix
    normalized in [0.0, 1.0] for lightweight JSON/WebSocket transmission to frontend.
    """
    # Normalize from typical dB range [-80, 0] to [0.0, 1.0]
    min_db = -80.0
    max_db = 0.0
    norm = np.clip((mel_db - min_db) / (max_db - min_db), 0.0, 1.0)

    n_mels, time_frames = norm.shape

    # Simple block-averaging downsampling
    row_step = max(1, n_mels // target_freq_bins)
    col_step = max(1, time_frames // target_time_steps)

    out_matrix = []
    for r in range(0, min(n_mels, target_freq_bins * row_step), row_step):
        row = []
        for c in range(0, min(time_frames, target_time_steps * col_step), col_step):
            block = norm[r : r + row_step, c : c + col_step]
            val = float(np.mean(block)) if block.size > 0 else 0.0
            row.append(round(val, 3))
        out_matrix.append(row)

    return out_matrix


def extract_all_features(
    audio_window: np.ndarray,
    sr: int = TARGET_SR,
    n_mels: int = DEFAULT_N_MELS,
    n_mfcc: int = DEFAULT_N_MFCC,
) -> Dict[str, Any]:
    """
    Extracts both Mel-Spectrogram and MFCC features for a given audio window.
    Returns numeric arrays and a visual matrix.
    """
    mel_db = extract_mel_spectrogram(audio_window, sr=sr, n_mels=n_mels)
    mfcc = extract_mfcc(audio_window, sr=sr, n_mfcc=n_mfcc, n_mels=n_mels)
    visual_matrix = render_spectrogram_to_matrix(mel_db)

    return {
        "mel_spectrogram": mel_db,
        "mel_shape": list(mel_db.shape),
        "mfcc": mfcc,
        "mfcc_shape": list(mfcc.shape),
        "visual_matrix": visual_matrix,
    }

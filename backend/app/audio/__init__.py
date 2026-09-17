"""
SHADOW-NET Audio Pipeline Package
Contains preprocessing, Voice Activity Detection (VAD), and acoustic feature extraction.
"""

from app.audio.preprocessing import load_audio, normalize_audio, resample_audio
from app.audio.vad import VADInterface, get_vad, SileroVAD, EnergyVAD
from app.audio.features import (
    slice_into_windows,
    extract_mel_spectrogram,
    extract_mfcc,
    extract_all_features,
    render_spectrogram_to_matrix,
)

__all__ = [
    "load_audio",
    "normalize_audio",
    "resample_audio",
    "VADInterface",
    "get_vad",
    "SileroVAD",
    "EnergyVAD",
    "slice_into_windows",
    "extract_mel_spectrogram",
    "extract_mfcc",
    "extract_all_features",
    "render_spectrogram_to_matrix",
]

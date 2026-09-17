"""
Base interface for SHADOW-NET deepfake voice detectors.
Provides pluggable abstraction for interchangeable ML architectures
(ResNet-18, CNN Baseline, Pretrained Audio Models, or Demo Fallback).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import numpy as np


class DetectorInterface(ABC):
    """
    Abstract contract for audio deepfake classification backends.
    Any model implementation must adhere to this interface so callers
    (Audio Pipeline, WebSocket streaming, Decision Engine) remain decoupled.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier name."""
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        """Operational mode: 'ml' (real trained inference) or 'demo' (synthetic fallback)."""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Indicates if production weights are currently active."""
        pass

    @abstractmethod
    def predict_window(self, mel_spectrogram: np.ndarray) -> Dict[str, Any]:
        """
        Runs inference on a single audio window's log-Mel-spectrogram.

        Args:
            mel_spectrogram: 2D numpy array of shape (n_mels, time_frames), typically (128, T).

        Returns:
            Dict containing:
                - fake_probability: float (0.0 to 1.0, probability that audio is deepfake)
                - real_probability: float (0.0 to 1.0, probability that audio is genuine)
                - raw_label: 'REAL' or 'DEEPFAKE'
                - confidence: float (0.0 to 1.0, confidence in the raw label)
                - raw_scores: List[float] (raw class logits or probabilities)
                - mode: 'ml' or 'demo'
        """
        pass

    def predict_windows(self, windows_features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch prediction over a list of window features.
        """
        results = []
        for w in windows_features:
            mel = w.get("mel_spectrogram")
            if mel is None:
                continue
            pred = self.predict_window(mel)
            pred["window_index"] = w.get("window_index", 0)
            pred["start_sec"] = w.get("start_sec", 0.0)
            pred["end_sec"] = w.get("end_sec", 0.0)
            results.append(pred)
        return results

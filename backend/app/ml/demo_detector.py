"""
Demo Fallback Detector for SHADOW-NET.
Provides realistic synthetic predictions when no trained ML weights (resnet18.pth) exist.

NOTICE:
Outputs from this class are explicitly labeled with mode='demo' and MUST NEVER
be presented as validated machine learning output.
"""

import logging
import hashlib
from typing import Dict, Any
import numpy as np

from app.ml.base import DetectorInterface

logger = logging.getLogger("shadow_net.ml.demo")


class DemoFallbackDetector(DetectorInterface):
    """
    Synthetic prediction fallback detector.
    Emits a prominent warning on startup and explicitly brands all outputs with mode='demo'.
    """

    def __init__(self):
        logger.warning(
            "====================================================================\n"
            "[WARNING] SHADOW-NET RUNNING IN DEMO MODE!\n"
            "No trained model weights found (or DEMO_MODE=True).\n"
            "Predictions are SYNTHETIC and generated for UI/system demonstration only.\n"
            "Do NOT use for actual security evaluation until weights are loaded.\n"
            "===================================================================="
        )

    @property
    def name(self) -> str:
        return "DemoFallbackDetector (Synthetic Heuristic)"

    @property
    def mode(self) -> str:
        return "demo"

    @property
    def is_loaded(self) -> bool:
        return False

    def predict_window(self, mel_spectrogram: np.ndarray) -> Dict[str, Any]:
        """
        Generates plausible synthetic deepfake probabilities based on spectral
        dynamics and deterministic hashing of the spectrogram content.
        """
        if mel_spectrogram.size == 0:
            return {
                "fake_probability": 0.50,
                "real_probability": 0.50,
                "raw_label": "UNCERTAIN",
                "confidence": 0.50,
                "raw_scores": [0.50, 0.50],
                "mode": self.mode,
                "model_name": self.name,
                "is_synthetic": True,
            }

        # Calculate lightweight spectral metrics to inform plausible variation
        high_band_energy = float(np.mean(mel_spectrogram[96:, :]))  # High frequencies
        mid_band_energy = float(np.mean(mel_spectrogram[32:96, :]))  # Mid frequencies
        spec_variance = float(np.var(mel_spectrogram))

        # Deterministic seed from spectral summary to keep predictions stable across same audio
        hash_seed = int(hashlib.md5(mel_spectrogram.tobytes()[:256]).hexdigest()[:8], 16)
        pseudo_rand = (hash_seed % 1000) / 1000.0  # Normalized [0.0, 1.0]

        # Synthesize a plausible score:
        # Synthetic speech artifacts often exhibit unusual high-band variance or flattened spectral rolloff
        score_base = 0.35 + 0.30 * pseudo_rand
        if spec_variance < 10.0:
            # Overly flat or unnatural spectrogram tends towards synthetic in demo
            score_base += 0.15

        fake_prob = float(np.clip(score_base, 0.05, 0.95))
        real_prob = float(1.0 - fake_prob)

        raw_label = "DEEPFAKE" if fake_prob >= 0.50 else "REAL"
        raw_conf = fake_prob if raw_label == "DEEPFAKE" else real_prob

        return {
            "fake_probability": round(fake_prob, 4),
            "real_probability": round(real_prob, 4),
            "raw_label": raw_label,
            "confidence": round(raw_conf, 4),
            "raw_scores": [round(real_prob, 4), round(fake_prob, 4)],
            "mode": self.mode,
            "model_name": self.name,
            "is_synthetic": True,
        }

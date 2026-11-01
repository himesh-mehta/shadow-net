"""
Production and Baseline Audio Classifiers for SHADOW-NET.
Adheres to the model artifact specification:
- Loads config and state from models/<model_name>/<version>/metadata.json
- Emits standardized detection outputs with explicit model_status and is_heuristic_placeholder flags
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

from app.ml.base import DetectorInterface
from app.ml.metadata import ModelMetadata, load_model_metadata

logger = logging.getLogger("shadow_net.ml.classifier")


class StandardizedAudioDetector(DetectorInterface):
    """
    Standardized detector interface supporting both trained ML inference
    and transparent untrained/experimental skeleton modes.
    """

    def __init__(
        self,
        metadata: Optional[ModelMetadata] = None,
        weights_dir: Optional[Path] = None,
        model_path: Optional[str] = None,
    ):
        self.metadata = metadata or load_model_metadata()
        self.weights_dir = weights_dir
        self.model_path = model_path
        self._model = None
        self._device = None
        self._torch = None
        self._is_loaded = False

        self._init_backend()

    def _init_backend(self):
        """Attempts to load PyTorch model and weights if available."""
        if not self.model_path and not self.weights_dir:
            return
        try:
            import torch
            self._torch = torch
            self._device = torch.device("cpu")

            # Check if weights file exists and is trained
            weights_path = None
            if self.model_path and os.path.isfile(self.model_path):
                weights_path = Path(self.model_path)
            elif self.weights_dir:
                candidate = self.weights_dir / (self.metadata.weights_file or "model.pt")
                if candidate.is_file():
                    weights_path = candidate

            if weights_path:
                logger.info(f"Loading weights from {weights_path}")
                checkpoint = torch.load(weights_path, map_location=self._device, weights_only=True)
                arch = checkpoint.get("model_name", self.metadata.architecture) if isinstance(checkpoint, dict) else self.metadata.architecture
                from app.ml.legacy_models import build_legacy_model
                net = build_legacy_model(arch)
                state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
                net.load_state_dict(state_dict)
                self.metadata.architecture = arch
                self._is_loaded = True
                self.metadata.is_trained = True
                self.metadata.status = "TRAINED"
                logger.info(f"Model successfully loaded trained weights from {weights_path}.")
            else:
                return

            net.to(self._device)
            net.eval()
            self._model = net

        except Exception as e:
            logger.warning(f"Could not load PyTorch model backend: {e}. Operating in heuristic placeholder mode.")
            self._model = None
            self._is_loaded = False

    @property
    def name(self) -> str:
        if self._is_loaded and self.is_trained:
            return f"Legacy {self.metadata.architecture} (experimental)"
        return self.metadata.model_name

    @property
    def version(self) -> str:
        return self.metadata.model_version

    @property
    def mode(self) -> str:
        return "ml" if (self._is_loaded and self.metadata.is_trained) else "demo"

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def is_trained(self) -> bool:
        return self.metadata.is_trained and self._is_loaded

    @property
    def model_status(self) -> str:
        return "TRAINED" if self.is_trained else "NOT_TRAINED"

    @property
    def is_heuristic_placeholder(self) -> bool:
        return not self.is_trained

    def predict_window(
        self,
        mel_spectrogram: np.ndarray,
        window_start: float = 0.0,
        window_end: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Runs inference on a single audio window's log-Mel-spectrogram.
        Returns the standardized schema:
        - ai_probability
        - real_probability
        - verdict ("REAL" | "AI_SUSPECTED" | "UNCERTAIN")
        - model_name
        - model_version
        - model_status ("NOT_TRAINED" | "TRAINED")
        - is_heuristic_placeholder (bool)
        - window_start
        - window_end
        """
        # If model is genuinely trained, run neural network
        if self.is_trained and self._model is not None and self._torch is not None:
            torch = self._torch
            mel_array = mel_spectrogram.astype(np.float32)
            tensor = torch.from_numpy(mel_array).unsqueeze(0).unsqueeze(0).to(self._device)

            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

            real_prob = float(probs[0])
            ai_prob = float(probs[1])
        else:
            # UNTRAINED MODEL: Compute acoustic spectral heuristic placeholder
            # NEVER fake high certainty or present this as trained ML output
            if mel_spectrogram.size == 0:
                ai_prob = 0.50
                real_prob = 0.50
            else:
                # Spectral roll-off & high frequency energy variance proxy
                spec_std = float(np.std(mel_spectrogram))
                spec_mean = float(np.mean(mel_spectrogram))
                # Normalized heuristic centered around 0.50 with mild variation
                heuristic = 0.50 + 0.10 * np.tanh((spec_std - 15.0) / 10.0)
                ai_prob = float(np.clip(heuristic, 0.30, 0.70))
                real_prob = float(1.0 - ai_prob)

        real_th = self.metadata.decision_thresholds.real_threshold
        ai_th = self.metadata.decision_thresholds.ai_suspected_threshold

        # Standardized 3-way verdict
        if ai_prob >= ai_th:
            verdict = "AI_SUSPECTED"
            confidence = ai_prob
        elif ai_prob < real_th:
            verdict = "REAL"
            confidence = real_prob
        else:
            verdict = "UNCERTAIN"
            confidence = 0.50

        raw_label = "DEEPFAKE" if ai_prob >= 0.50 else "REAL"

        return {
            "ai_probability": round(ai_prob, 4),
            "real_probability": round(real_prob, 4),
            "verdict": verdict,
            "model_name": self.name,
            "model_version": self.version,
            "model_status": self.model_status,
            "is_heuristic_placeholder": self.is_heuristic_placeholder,
            "window_start": round(window_start, 2),
            "window_end": round(window_end, 2),
            # Backward compatibility fields
            "fake_probability": round(ai_prob, 4),
            "confidence": round(confidence, 4),
            "raw_label": raw_label,
            "raw_scores": [round(real_prob, 4), round(ai_prob, 4)],
            "mode": self.mode,
            "is_synthetic": self.is_heuristic_placeholder,
        }


# Maintain backward-compatible alias
ResNet18AudioClassifier = StandardizedAudioDetector

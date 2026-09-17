"""
ResNet-18 Audio Classifier for SHADOW-NET.
Adapts torchvision ResNet-18 for 1-channel log Mel-Spectrogram input
and binary classification (Real vs. Deepfake).
"""

import os
import logging
from typing import Dict, Any, Optional
import numpy as np

from app.ml.base import DetectorInterface

logger = logging.getLogger("shadow_net.ml.classifier")


class ResNet18AudioClassifier(DetectorInterface):
    """
    Production deepfake voice classifier using an adapted ResNet-18 architecture.
    Accepts 1-channel log-Mel-spectrogram inputs (1, 128, T) and predicts binary classes.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._model = None
        self._device = None
        self._is_loaded = False
        self._torch = None
        self._init_architecture()

    def _init_architecture(self):
        try:
            import torch
            import torch.nn as nn
            import torchvision.models as models

            self._torch = torch
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            # Build ResNet-18 backbone
            net = models.resnet18(weights=None)

            # Adapt first conv layer: change in_channels from 3 (RGB) to 1 (Spectrogram)
            net.conv1 = nn.Conv2d(
                in_channels=1,
                out_channels=64,
                kernel_size=7,
                stride=2,
                padding=3,
                bias=False,
            )

            # Adapt final linear layer: 2 output classes (Index 0: Real, Index 1: Deepfake)
            num_features = net.fc.in_features
            net.fc = nn.Linear(num_features, 2)

            # Load checkpoint weights if file exists
            if self.model_path and os.path.isfile(self.model_path):
                logger.info(f"Loading trained model weights from: {self.model_path}")
                checkpoint = torch.load(self.model_path, map_location=self._device)
                # Support checkpoint saved as state_dict or wrapped dict
                state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
                net.load_state_dict(state_dict)
                self._is_loaded = True
                logger.info("ResNet-18 model weights loaded successfully.")
            else:
                logger.warning(f"No checkpoint found at '{self.model_path}'. Model has randomly initialized weights.")
                self._is_loaded = False

            net.to(self._device)
            net.eval()
            self._model = net

        except Exception as e:
            logger.error(f"Failed to initialize ResNet-18 classifier: {e}")
            self._model = None
            self._is_loaded = False

    @property
    def name(self) -> str:
        return "ResNet18AudioClassifier (1-Channel Spectrogram)"

    @property
    def mode(self) -> str:
        return "ml" if self._is_loaded else "demo"

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def predict_window(self, mel_spectrogram: np.ndarray) -> Dict[str, Any]:
        """
        Infers real vs deepfake probabilities from a 2D Mel-spectrogram array.
        Shape expected: (n_mels, time_frames), e.g. (128, 63).
        """
        if self._model is None or self._torch is None:
            raise RuntimeError("ResNet-18 model is not initialized.")

        torch = self._torch

        # Ensure 4D tensor: (batch_size=1, channels=1, n_mels=128, time_frames=T)
        mel_array = mel_spectrogram.astype(np.float32)
        tensor = torch.from_numpy(mel_array).unsqueeze(0).unsqueeze(0).to(self._device)

        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

        real_prob = float(probs[0])
        fake_prob = float(probs[1])

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
            "is_synthetic": not self._is_loaded,
        }

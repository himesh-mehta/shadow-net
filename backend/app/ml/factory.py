"""
Detector Factory & Lifecycle Manager for SHADOW-NET.
Resolves model weights at MODEL_PATH, initializes the appropriate detector
(ResNet-18 or DemoFallbackDetector), and provides thread-safe access.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.ml.base import DetectorInterface
from app.ml.demo_detector import DemoFallbackDetector
from app.ml.classifier import ResNet18AudioClassifier

logger = logging.getLogger("shadow_net.ml.factory")

_CURRENT_DETECTOR: Optional[DetectorInterface] = None


def resolve_model_path(configured_path: str) -> Optional[Path]:
    """
    Resolves the model path across backend, project root, and absolute paths.
    """
    p = Path(configured_path)
    if p.is_file():
        return p.resolve()

    # Try relative to backend root
    backend_dir = Path(__file__).resolve().parent.parent.parent
    candidate_1 = (backend_dir / configured_path).resolve()
    if candidate_1.is_file():
        return candidate_1

    # Try relative to project root (e.g. shadow-net/model/resnet18.pth)
    project_root = backend_dir.parent
    candidate_2 = (project_root / configured_path).resolve()
    if candidate_2.is_file():
        return candidate_2

    candidate_3 = project_root / "model" / "resnet18.pth"
    if candidate_3.is_file():
        return candidate_3

    return None


def get_detector(force_reload: bool = False) -> DetectorInterface:
    """
    Returns the active detector instance (cached singleton).
    Switches to ResNet18AudioClassifier if MODEL_PATH exists and DEMO_MODE is False.
    Otherwise falls back to DemoFallbackDetector.
    """
    global _CURRENT_DETECTOR

    if _CURRENT_DETECTOR is not None and not force_reload:
        return _CURRENT_DETECTOR

    settings = get_settings()
    resolved_path = resolve_model_path(settings.MODEL_PATH)

    if resolved_path is not None and not settings.DEMO_MODE:
        logger.info(f"Model file detected at: {resolved_path}. Initializing ResNet-18 classifier.")
        classifier = ResNet18AudioClassifier(str(resolved_path))
        if classifier.is_loaded:
            _CURRENT_DETECTOR = classifier
            return _CURRENT_DETECTOR
        else:
            logger.warning("ResNet-18 weights failed to load. Falling back to DemoFallbackDetector.")

    # Fallback to Demo mode
    _CURRENT_DETECTOR = DemoFallbackDetector()
    return _CURRENT_DETECTOR


def reload_detector() -> DetectorInterface:
    """Forces reloading the active detector from disk."""
    return get_detector(force_reload=True)

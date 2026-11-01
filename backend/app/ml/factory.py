"""
Detector Factory & Lifecycle Manager for SHADOW-NET.
Loads active model artifacts according to the directory structure:
    models/<ACTIVE_MODEL_NAME>/<ACTIVE_MODEL_VERSION>/
with companion metadata.json and weights, and supports legacy MODEL_PATH resolution.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.ml.base import DetectorInterface
from app.ml.metadata import load_model_metadata
from app.ml.classifier import StandardizedAudioDetector
from app.ml.demo_detector import DemoFallbackDetector

logger = logging.getLogger("shadow_net.ml.factory")

_CURRENT_DETECTOR: Optional[DetectorInterface] = None


def resolve_model_dir(models_dir: str, model_name: str, model_version: str) -> Optional[Path]:
    """
    Locates the model directory models/<model_name>/<model_version>/.
    """
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent

    candidates = [
        project_root / models_dir / model_name / model_version,
        backend_dir / models_dir / model_name / model_version,
        Path.cwd() / models_dir / model_name / model_version,
    ]

    for c in candidates:
        if c.is_dir():
            return c.resolve()

    return None


def resolve_model_path(configured_path: str) -> Optional[Path]:
    """
    Resolves a direct weights checkpoint path across backend, project root, and relative paths.
    """
    p = Path(configured_path)
    if p.is_file():
        return p.resolve()

    backend_dir = Path(__file__).resolve().parent.parent.parent
    candidate_1 = (backend_dir / configured_path).resolve()
    if candidate_1.is_file():
        return candidate_1

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
    Reads configuration from app settings:
    - MODELS_DIR
    - ACTIVE_MODEL_NAME
    - ACTIVE_MODEL_VERSION
    - DEMO_MODE & MODEL_PATH
    """
    global _CURRENT_DETECTOR

    if _CURRENT_DETECTOR is not None and not force_reload:
        return _CURRENT_DETECTOR

    settings = get_settings()
    model_name = getattr(settings, "ACTIVE_MODEL_NAME", "shadownet-audio-detector")
    model_version = getattr(settings, "ACTIVE_MODEL_VERSION", "v1")
    models_dir = getattr(settings, "MODELS_DIR", "models")
    demo_mode = getattr(settings, "DEMO_MODE", True)
    model_path_str = getattr(settings, "MODEL_PATH", "")

    weights_dir = resolve_model_dir(models_dir, model_name, model_version)
    metadata = load_model_metadata(models_dir, model_name, model_version)

    # Check if a direct trained model path is configured and DEMO_MODE is False
    resolved_file = resolve_model_path(model_path_str) if model_path_str else None
    if not demo_mode and resolved_file is not None:
        logger.info(f"Production ML mode active: loading weights from {resolved_file}")
        detector = StandardizedAudioDetector(
            metadata=metadata,
            model_path=str(resolved_file),
        )
        if detector.is_loaded:
            _CURRENT_DETECTOR = detector
            return _CURRENT_DETECTOR

    logger.info(
        f"Initializing detector: {metadata.model_name}:{metadata.model_version} "
        f"(status={metadata.status}, is_trained={metadata.is_trained})"
    )

    detector = StandardizedAudioDetector(metadata=metadata, weights_dir=weights_dir)
    _CURRENT_DETECTOR = detector
    return _CURRENT_DETECTOR


def reload_detector() -> DetectorInterface:
    """Forces reloading the active detector from disk."""
    return get_detector(force_reload=True)

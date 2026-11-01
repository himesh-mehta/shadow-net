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
from app.ml.pretrained import PretrainedAudioDetector, DetectorUnavailable
from threading import RLock

logger = logging.getLogger("shadow_net.ml.factory")

_CURRENT_DETECTOR: Optional[DetectorInterface] = None
_CURRENT_KEY = None
_LAST_ERROR = None
_REQUESTED_DEMO = None
_LOCK = RLock()


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


def get_detector(force_reload: bool = False, demo_mode: Optional[bool] = None) -> DetectorInterface:
    """Cache by effective mode AND model configuration; never fall back silently in ML mode."""
    global _CURRENT_DETECTOR, _CURRENT_KEY, _LAST_ERROR, _REQUESTED_DEMO
    settings = get_settings()
    demo = settings.DEMO_MODE if demo_mode is None else demo_mode
    key = (demo, settings.DETECTOR_BACKEND, settings.HF_MODEL_ID, settings.HF_MODEL_REVISION,
           settings.HF_LOCAL_FILES_ONLY, settings.INFERENCE_DEVICE, settings.CPU_THREADS, settings.MODEL_PATH,
           settings.MODELS_DIR, settings.ACTIVE_MODEL_NAME, settings.ACTIVE_MODEL_VERSION)
    with _LOCK:
        _REQUESTED_DEMO = demo
        if _CURRENT_DETECTOR is not None and _CURRENT_KEY == key and not force_reload:
            return _CURRENT_DETECTOR
        try:
            metadata = load_model_metadata(settings.MODELS_DIR, settings.ACTIVE_MODEL_NAME, settings.ACTIVE_MODEL_VERSION)
            if demo:
                # No weights, downloads, or random neural network in demo mode.
                metadata.is_trained = False
                metadata.status = "NOT_TRAINED"
                detector = StandardizedAudioDetector(metadata=metadata)
            elif settings.DETECTOR_BACKEND == "huggingface":
                detector = PretrainedAudioDetector(
                    settings.HF_MODEL_ID, settings.HF_MODEL_REVISION,
                    settings.HF_LOCAL_FILES_ONLY, settings.INFERENCE_DEVICE, settings.CPU_THREADS,
                )
            elif settings.DETECTOR_BACKEND == "legacy":
                resolved = resolve_model_path(settings.MODEL_PATH)
                weights_dir = resolve_model_dir(settings.MODELS_DIR, settings.ACTIVE_MODEL_NAME, settings.ACTIVE_MODEL_VERSION)
                detector = StandardizedAudioDetector(metadata=metadata, model_path=str(resolved) if resolved else None,
                                                     weights_dir=weights_dir)
                if not detector.is_loaded:
                    raise DetectorUnavailable("Legacy checkpoint missing or incompatible. No inference was performed.")
            else:
                raise DetectorUnavailable("Unknown DETECTOR_BACKEND. Use huggingface or legacy.")
        except Exception as exc:
            _LAST_ERROR = str(exc)
            raise DetectorUnavailable(str(exc)) from exc
        _CURRENT_DETECTOR, _CURRENT_KEY, _LAST_ERROR = detector, key, None
        return detector


def reload_detector(demo_mode: Optional[bool] = None) -> DetectorInterface:
    return get_detector(force_reload=True, demo_mode=demo_mode)


def detector_status() -> dict:
    """Inspect state without initiating a model download or load."""
    detector = _CURRENT_DETECTOR
    return {
        "requested_demo_mode": _REQUESTED_DEMO,
        "mode": detector.mode if detector else "unavailable",
        "loaded": bool(detector and detector.is_loaded),
        "model_name": detector.name if detector else None,
        "model_version": getattr(detector, "version", None),
        "model_status": getattr(detector, "model_status", "UNAVAILABLE"),
        "validation_status": getattr(detector, "validation_status", "NOT_LOCALLY_VALIDATED"),
        "score_type": "uncalibrated_softmax" if detector and detector.is_loaded else "demo_placeholder",
        "error": _LAST_ERROR,
    }

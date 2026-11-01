"""
Model Metadata Manager for SHADOW-NET.
Loads and validates metadata.json for models stored under models/<name>/<version>/.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger("shadow_net.ml.metadata")


class FeatureConfig(BaseModel):
    sample_rate: int = 16000
    channels: int = 1
    window_seconds: float = 2.0
    hop_seconds: float = 1.0
    n_mels: int = 128
    n_fft: int = 1024
    hop_length: int = 512
    f_min: float = 20.0
    f_max: float = 8000.0
    normalized: bool = True


class DecisionThresholds(BaseModel):
    real_threshold: float = 0.35
    ai_suspected_threshold: float = 0.65
    calibrated: bool = False


class ModelMetadata(BaseModel):
    model_name: str
    model_version: str
    architecture: str
    is_trained: bool = False
    status: str = "NOT_TRAINED"  # "NOT_TRAINED" | "TRAINED"
    description: str = ""
    training_date: Optional[str] = None
    dataset_version: Optional[str] = None
    weights_file: Optional[str] = "model.pt"
    feature_config: FeatureConfig = Field(default_factory=FeatureConfig)
    validation_metrics: Optional[Dict[str, Any]] = None
    decision_thresholds: DecisionThresholds = Field(default_factory=DecisionThresholds)
    trained_on: List[str] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)


def load_model_metadata(
    models_dir: str = "models",
    model_name: str = "shadownet-audio-detector",
    model_version: str = "v1",
) -> ModelMetadata:
    """
    Locates and parses metadata.json for the specified model and version.
    Searches relative to project root, backend root, or working directory.
    """
    # Try multiple base search paths
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent

    candidate_paths = [
        project_root / models_dir / model_name / model_version / "metadata.json",
        backend_dir / models_dir / model_name / model_version / "metadata.json",
        Path.cwd() / models_dir / model_name / model_version / "metadata.json",
        Path.cwd().parent / models_dir / model_name / model_version / "metadata.json",
    ]

    for p in candidate_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                metadata = ModelMetadata(**data)
                logger.info(f"Loaded model metadata from: {p} (status={metadata.status}, is_trained={metadata.is_trained})")
                return metadata
            except Exception as e:
                logger.error(f"Error parsing metadata file {p}: {e}")

    logger.warning(
        f"No metadata.json found for {model_name}/{model_version}. Using default untrained metadata."
    )
    return ModelMetadata(
        model_name=model_name,
        model_version=model_version,
        architecture="lcnn_spectrogram",
        is_trained=False,
        status="NOT_TRAINED",
        description="Default unconfigured model skeleton",
        known_limitations=["Untrained baseline skeleton. Detection probabilities are heuristic placeholders."],
    )

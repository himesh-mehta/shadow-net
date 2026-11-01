"""Download only pinned public model assets, never repository Python or pickle files."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import get_settings


def main():
    from huggingface_hub import snapshot_download
    settings = get_settings()
    path = snapshot_download(
        settings.HF_MODEL_ID, revision=settings.HF_MODEL_REVISION,
        allow_patterns=["config.json", "preprocessor_config.json", "model.safetensors", "README.md", "LICENSE*"],
    )
    print(f"Downloaded {settings.HF_MODEL_ID}@{settings.HF_MODEL_REVISION} to {path}")
    from app.ml.pretrained import PretrainedAudioDetector
    detector = PretrainedAudioDetector(settings.HF_MODEL_ID, settings.HF_MODEL_REVISION, True)
    print(f"Load check passed; sample rate={detector.sample_rate}; fake class index={detector.fake_index}")
    print("This confirms loading only. Evaluate human and generated speech before making accuracy claims.")


if __name__ == "__main__":
    main()

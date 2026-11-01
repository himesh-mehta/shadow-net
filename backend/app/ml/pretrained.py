"""Local Wav2Vec2 audio classification adapter. No remote Python execution or fallback."""
from threading import Lock
from typing import Any, Dict

import numpy as np

from app.ml.base import DetectorInterface


class DetectorUnavailable(RuntimeError):
    pass


def resolve_fake_index(id2label: dict) -> int:
    """Never assume the old ResNet's [real, fake] ordering for a new model."""
    labels = {int(i): str(label).strip().lower() for i, label in id2label.items()}
    fake = [i for i, label in labels.items() if label in {"fake", "spoof", "deepfake"}]
    real = [i for i, label in labels.items() if label in {"real", "bonafide", "bona-fide"}]
    if len(labels) != 2 or len(fake) != 1 or len(real) != 1 or set(labels) != {0, 1}:
        raise DetectorUnavailable(f"Unsupported class mapping: {labels}. Explicit real/fake labels required.")
    return fake[0]


class PretrainedAudioDetector(DetectorInterface):
    uses_waveform = True
    model_status = "TRAINED"
    is_heuristic_placeholder = False
    validation_status = "NOT_LOCALLY_VALIDATED"

    def __init__(self, model_id: str, revision: str, local_files_only: bool = True, device: str = "cpu", cpu_threads: int = 2):
        self.model_id, self.revision = model_id, revision
        self._lock = Lock()
        try:
            import torch
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
            self._torch = torch
            if device == "cpu":
                torch.set_num_threads(max(1, cpu_threads))
            self.device = torch.device(device)
            common = dict(revision=revision, local_files_only=local_files_only, trust_remote_code=False)
            self.extractor = AutoFeatureExtractor.from_pretrained(model_id, **common)
            self.model, loading_info = AutoModelForAudioClassification.from_pretrained(
                model_id, use_safetensors=True, output_loading_info=True, **common
            )
            if loading_info.get("missing_keys") or loading_info.get("mismatched_keys") or loading_info.get("error_msgs"):
                raise DetectorUnavailable("Checkpoint did not fully initialize the classifier.")
            self.model.to(self.device).eval()
            self.fake_index = resolve_fake_index(self.model.config.id2label)
            self.sample_rate = int(self.extractor.sampling_rate)
            if self.sample_rate != 16000:
                raise DetectorUnavailable("This prototype currently supports 16 kHz detector models only.")
        except Exception as exc:
            raise DetectorUnavailable(
                f"Pretrained detector could not load ({type(exc).__name__}). "
                "Run python scripts/download_detector.py in the project environment, "
                "then retry ML mode. Demo mode remains available."
            ) from exc

    @property
    def name(self):
        return self.model_id

    @property
    def version(self):
        return self.revision

    @property
    def mode(self):
        return "ml"

    @property
    def is_loaded(self):
        return True

    @property
    def is_trained(self):
        return True

    def predict_window(self, mel_spectrogram, **kwargs):
        raise ValueError("Wav2Vec2 requires a raw waveform. Use predict_audio(), not a Mel spectrogram.")

    def predict_audio(self, audio: np.ndarray, sr: int = 16000, window_start=0.0, window_end=None) -> Dict[str, Any]:
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim != 1 or sr != self.sample_rate or not np.isfinite(audio).all():
            raise ValueError("Expected finite mono audio at the detector's sample rate.")
        if audio.size < sr // 2:
            raise ValueError("At least 0.5 seconds of audio is required per model window.")
        if audio.size > 5 * sr:
            raise ValueError("Model windows are limited to five seconds; split longer audio first.")
        inputs = self.extractor(audio, sampling_rate=sr, return_tensors="pt", padding=False)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self._lock, self._torch.inference_mode():
            logits = self.model(**inputs).logits
            if logits.shape != (1, 2) or not self._torch.isfinite(logits).all():
                raise DetectorUnavailable("Detector returned invalid class scores.")
            scores = self._torch.softmax(logits, dim=-1)[0].cpu().tolist()
        fake = float(scores[self.fake_index])
        real = 1.0 - fake
        verdict = "AI_SUSPECTED" if fake >= 0.65 else "REAL" if fake < 0.35 else "UNCERTAIN"
        return dict(
            ai_probability=fake, fake_probability=fake, real_probability=real,
            confidence=max(fake, real) if verdict != "UNCERTAIN" else 0.5,
            verdict=verdict, raw_label="DEEPFAKE" if fake >= 0.5 else "REAL",
            raw_scores=[real, fake], mode="ml", model_name=self.name, model_version=self.version,
            model_status=self.model_status, is_heuristic_placeholder=False, is_synthetic=False,
            validation_status=self.validation_status, score_type="uncalibrated_softmax",
            window_start=window_start,
            window_end=window_end if window_end is not None else window_start + audio.size / sr,
        )

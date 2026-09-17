"""
Voice Activity Detection (VAD) module for SHADOW-NET.
Provides an abstract VADInterface and concrete implementations:
- EnergyVAD (robust offline energy/RMS VAD via librosa)
- SileroVAD (deep learning neural VAD with graceful fallback)
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import numpy as np
import librosa

logger = logging.getLogger("shadow_net.audio.vad")


class VADInterface(ABC):
    """
    Abstract interface for Voice Activity Detection implementations.
    Allows swapping detection algorithms without modifying client callers.
    """

    @abstractmethod
    def filter_speech(
        self,
        audio: np.ndarray,
        sr: int = 16000,
        sensitivity: int = 2,
    ) -> Tuple[np.ndarray, List[Dict[str, float]], Dict[str, Any]]:
        """
        Filters silence from the input audio, retaining speech segments.

        Args:
            audio: 1D normalized float32 waveform.
            sr: Sampling rate (typically 16000).
            sensitivity: VAD aggressiveness level (0 to 3, higher drops more background noise).

        Returns:
            Tuple containing:
                - speech_audio (np.ndarray): Concatenated active speech frames.
                - intervals (List[Dict[str, float]]): List of {"start_sec": float, "end_sec": float}.
                - metadata (Dict[str, Any]): Stats including original duration, speech duration, dropped silence.
        """
        pass


class EnergyVAD(VADInterface):
    """
    Acoustic Energy and RMS-based VAD using librosa.effects.split.
    Zero-network dependency, completely deterministic and fast.
    """

    # Maps sensitivity level (0-3) to top_db threshold below peak
    SENSITIVITY_TOP_DB = {
        0: 40,  # Very permissive: keeps lower energy sounds
        1: 32,  # Moderately permissive
        2: 24,  # Balanced (default)
        3: 16,  # Aggressive: drops anything except loud speech
    }

    def filter_speech(
        self,
        audio: np.ndarray,
        sr: int = 16000,
        sensitivity: int = 2,
    ) -> Tuple[np.ndarray, List[Dict[str, float]], Dict[str, Any]]:
        if audio.size == 0:
            return audio, [], {"original_duration": 0.0, "speech_duration": 0.0, "dropped_duration": 0.0}

        orig_duration = float(len(audio) / sr)
        top_db = self.SENSITIVITY_TOP_DB.get(sensitivity, 24)

        # Split into non-silent intervals
        intervals = librosa.effects.split(
            y=audio,
            top_db=top_db,
            frame_length=1024,
            hop_length=256,
        )

        if len(intervals) == 0:
            # Fallback: if entire audio was under top_db, check if it's pure silence
            peak = np.max(np.abs(audio))
            if peak < 0.01:
                # Pure silence
                return (
                    np.zeros(0, dtype=np.float32),
                    [],
                    {"original_duration": orig_duration, "speech_duration": 0.0, "dropped_duration": orig_duration}
                )
            else:
                # Retain audio as a single chunk
                return (
                    audio,
                    [{"start_sec": 0.0, "end_sec": orig_duration}],
                    {"original_duration": orig_duration, "speech_duration": orig_duration, "dropped_duration": 0.0}
                )

        speech_chunks = [audio[start:end] for start, end in intervals]
        speech_audio = np.concatenate(speech_chunks) if speech_chunks else np.zeros(0, dtype=np.float32)

        formatted_intervals = [
            {"start_sec": round(float(start / sr), 4), "end_sec": round(float(end / sr), 4)}
            for start, end in intervals
        ]

        speech_duration = float(len(speech_audio) / sr)
        dropped_duration = max(0.0, orig_duration - speech_duration)

        return (
            speech_audio,
            formatted_intervals,
            {
                "original_duration": round(orig_duration, 4),
                "speech_duration": round(speech_duration, 4),
                "dropped_duration": round(dropped_duration, 4),
                "vad_engine": "EnergyVAD",
            },
        )


class SileroVAD(VADInterface):
    """
    Neural Voice Activity Detector using Silero VAD (torch hub or ONNX).
    Falls back to EnergyVAD if dependencies or weights are not reachable.
    """

    def __init__(self):
        self._model = None
        self._utils = None
        self._fallback = EnergyVAD()
        self._initialized = False

    def _init_model(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            self._utils = utils
            logger.info("Silero VAD model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Silero VAD ({e}). Using EnergyVAD fallback.")
            self._model = None

    def filter_speech(
        self,
        audio: np.ndarray,
        sr: int = 16000,
        sensitivity: int = 2,
    ) -> Tuple[np.ndarray, List[Dict[str, float]], Dict[str, Any]]:
        self._init_model()

        if self._model is None:
            return self._fallback.filter_speech(audio, sr=sr, sensitivity=sensitivity)

        try:
            import torch
            (get_speech_timestamps, _, _, _, _) = self._utils
            tensor_audio = torch.from_numpy(audio)

            # Map sensitivity (0-3) to threshold (higher sensitivity -> lower threshold for speech)
            threshold_map = {0: 0.65, 1: 0.55, 2: 0.50, 3: 0.35}
            threshold = threshold_map.get(sensitivity, 0.50)

            timestamps = get_speech_timestamps(
                tensor_audio,
                self._model,
                threshold=threshold,
                sampling_rate=sr,
            )

            if not timestamps:
                return (
                    np.zeros(0, dtype=np.float32),
                    [],
                    {
                        "original_duration": round(len(audio) / sr, 4),
                        "speech_duration": 0.0,
                        "dropped_duration": round(len(audio) / sr, 4),
                        "vad_engine": "SileroVAD",
                    }
                )

            speech_chunks = [audio[ts["start"]:ts["end"]] for ts in timestamps]
            speech_audio = np.concatenate(speech_chunks)

            formatted_intervals = [
                {"start_sec": round(float(ts["start"] / sr), 4), "end_sec": round(float(ts["end"] / sr), 4)}
                for ts in timestamps
            ]

            orig_dur = float(len(audio) / sr)
            speech_dur = float(len(speech_audio) / sr)

            return (
                speech_audio,
                formatted_intervals,
                {
                    "original_duration": round(orig_dur, 4),
                    "speech_duration": round(speech_dur, 4),
                    "dropped_duration": round(max(0.0, orig_dur - speech_dur), 4),
                    "vad_engine": "SileroVAD",
                },
            )
        except Exception as e:
            logger.warning(f"Silero VAD execution error ({e}). Falling back to EnergyVAD.")
            return self._fallback.filter_speech(audio, sr=sr, sensitivity=sensitivity)


def get_vad(preference: str = "auto") -> VADInterface:
    """
    Factory function returning the configured VAD implementation.
    """
    if preference == "silero":
        return SileroVAD()
    elif preference == "energy":
        return EnergyVAD()
    # Auto: default to EnergyVAD for instant deterministic local execution,
    # or Silero if preferred in config
    return EnergyVAD()

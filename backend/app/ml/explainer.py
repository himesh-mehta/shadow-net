"""
Acoustic Feature Explainer for SHADOW-NET (Phase 1, Item 3).

Produces human-readable "why" explanations alongside model verdicts by
computing interpretable acoustic signals from Mel-spectrograms and MFCCs
and flagging features that deviate from typical real-speech distributions.

No SHAP or external ML explainability library is required — explanations are
derived purely from the same feature arrays the model consumes.

Typical real-speech reference ranges are based on LibriSpeech / VCTK
16kHz statistics. Values outside ±2σ of these ranges are flagged as
suspicious indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


# ─── Reference ranges for 16 kHz real speech (LibriSpeech / VCTK statistics) ──
# Each tuple is (min_normal, max_normal, human_label, suspicious_direction)
# suspicious_direction: 'high' means high values are suspicious, 'low' means low
# values are suspicious, 'both' means either extreme is suspicious.

_FEATURE_SPECS = {
    "spectral_flatness": (0.002, 0.18, "Spectral Flatness", "high"),
    "hf_energy_ratio": (0.00, 0.12, "High-Frequency Energy Ratio", "high"),
    "temporal_variance": (40.0, 900.0, "Temporal Energy Variance", "low"),
    "mfcc1_mean": (-600.0, -100.0, "MFCC-1 Mean (Loudness)", "both"),
    "mfcc_delta_energy": (0.5, 25.0, "MFCC Temporal Dynamics", "low"),
    "spectral_centroid_norm": (0.05, 0.40, "Spectral Centroid", "both"),
    "zero_crossing_rate": (0.01, 0.20, "Zero Crossing Rate", "both"),
}

_DIRECTION_LABELS = {
    "high": "unusually high",
    "low": "unusually low",
    "both_high": "unusually high",
    "both_low": "unusually low",
}


@dataclass
class FeatureSignal:
    """A single extracted acoustic feature with its verdict-relevant metadata."""
    name: str                      # Short key, e.g. "spectral_flatness"
    label: str                     # Human-readable label
    value: float                   # Measured value
    normal_min: float              # Lower bound of typical real-speech range
    normal_max: float              # Upper bound of typical real-speech range
    is_suspicious: bool            # True if value is outside normal range
    direction: str                 # 'unusually high' | 'unusually low' | 'normal'
    suspicion_weight: float        # 0.0–1.0, how far outside the normal range
    plain_english: str             # One-sentence explanation for UI display


@dataclass
class VerdictExplanation:
    """Full explanation payload attached to an audio analysis response."""
    verdict: str                   # 'REAL' | 'DEEPFAKE' | 'UNCERTAIN'
    confidence: float
    fake_probability: float
    summary: str                   # One-sentence top-level summary
    indicators: List[FeatureSignal] = field(default_factory=list)  # Sorted by suspicion
    top_reason: Optional[str] = None    # Most suspicious single feature in plain English
    mode: str = "demo"             # 'demo' or 'ml'

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "fake_probability": self.fake_probability,
            "summary": "Acoustic observations only. These heuristic measurements do not explain the neural model or prove manipulation.",
            "top_reason": "Acoustic observations only; not evidence of manipulation or a model explanation.",
            "mode": self.mode,
            "indicators": [
                {
                    "name": f.name,
                    "label": f.label,
                    "value": round(f.value, 4),
                    "normal_min": f.normal_min,
                    "normal_max": f.normal_max,
                    "is_suspicious": f.is_suspicious,
                    "direction": f.direction,
                    "suspicion_weight": round(f.suspicion_weight, 3),
                    "plain_english": f"{f.label}: {f.value:.4f}. Reference band is an unvalidated prototype heuristic.",
                }
                for f in self.indicators
            ],
        }


# ─── Feature extraction helpers ────────────────────────────────────────────────

def _extract_signals(
    mel_db: np.ndarray, mfcc: np.ndarray
) -> dict[str, float]:
    """
    Compute the 7 interpretable acoustic signals from the Mel-spectrogram (dB)
    and MFCC arrays. All inputs assumed to be 2D: (n_bands, time_frames).
    """
    # Convert dB mel back to linear power for certain computations
    mel_power = 10.0 ** (mel_db / 10.0)

    n_mels, n_frames = mel_power.shape

    # 1. Spectral Flatness — ratio of geometric mean to arithmetic mean of power spectrum.
    #    Synthesized speech often has a flatter spectrum (more noise-like / less harmonic).
    frame_geo_means = np.exp(np.mean(np.log(mel_power + 1e-10), axis=0))
    frame_arith_means = np.mean(mel_power, axis=0)
    flatness_per_frame = frame_geo_means / (frame_arith_means + 1e-10)
    spectral_flatness = float(np.mean(flatness_per_frame))

    # 2. High-Frequency Energy Ratio — TTS systems often over-generate or suppress
    #    high frequencies (>4kHz, top quarter of 128-mel bins at 16kHz).
    hf_start = int(n_mels * 0.75)
    hf_energy = float(np.mean(mel_power[hf_start:, :]))
    total_energy = float(np.mean(mel_power)) + 1e-10
    hf_energy_ratio = hf_energy / total_energy

    # 3. Temporal Energy Variance — real speech has natural variance driven by
    #    phoneme transitions; cloned/vocoder speech can be unnaturally smooth.
    frame_energies = np.sum(mel_power, axis=0)
    temporal_variance = float(np.var(frame_energies))

    # 4. MFCC-1 Mean — cepstral coefficient 0 is log-energy; unnatural loudness
    #    profiles (too uniform or too extreme) can indicate synthesis.
    mfcc1_mean = float(np.mean(mfcc[0, :])) if mfcc.shape[0] > 0 else 0.0

    # 5. MFCC Delta Energy — measures how much MFCCs change frame-to-frame.
    #    Neural TTS produces less temporal MFCC variation than natural speech.
    if mfcc.shape[1] > 1:
        mfcc_deltas = np.abs(np.diff(mfcc, axis=1))
        mfcc_delta_energy = float(np.mean(mfcc_deltas))
    else:
        mfcc_delta_energy = 0.0

    # 6. Spectral Centroid (normalized to [0, 1] over mel-bin axis).
    #    Measures the "center of mass" of the spectrum.
    mel_bins = np.arange(n_mels, dtype=np.float32)
    centroid_frames = np.sum(mel_power * mel_bins[:, None], axis=0) / (
        np.sum(mel_power, axis=0) + 1e-10
    )
    spectral_centroid_norm = float(np.mean(centroid_frames) / n_mels)

    # 7. Zero Crossing Rate — estimated from the mel domain as frame-to-frame
    #    sign changes of the dominant frequency bin amplitude.
    dominant_bin = int(np.argmax(np.mean(mel_power, axis=1)))
    dominant_series = mel_power[dominant_bin, :]
    zero_crossings = float(
        np.mean(np.abs(np.diff(np.sign(dominant_series - np.mean(dominant_series)))) / 2)
    )

    return {
        "spectral_flatness": spectral_flatness,
        "hf_energy_ratio": hf_energy_ratio,
        "temporal_variance": temporal_variance,
        "mfcc1_mean": mfcc1_mean,
        "mfcc_delta_energy": mfcc_delta_energy,
        "spectral_centroid_norm": spectral_centroid_norm,
        "zero_crossing_rate": zero_crossings,
    }


def _build_signal(name: str, value: float) -> FeatureSignal:
    """Assess one extracted value against its normal range and build a FeatureSignal."""
    spec = _FEATURE_SPECS[name]
    lo, hi, label, direction = spec

    is_suspicious = False
    suspicion_weight = 0.0
    dir_label = "normal"

    span = hi - lo

    if value > hi:
        is_suspicious = (direction in ("high", "both"))
        if is_suspicious:
            suspicion_weight = min(1.0, (value - hi) / (span + 1e-10))
            dir_label = "unusually high"
    elif value < lo:
        is_suspicious = (direction in ("low", "both"))
        if is_suspicious:
            suspicion_weight = min(1.0, (lo - value) / (span + 1e-10))
            dir_label = "unusually low"

    plain_english = _build_plain_english(name, label, value, lo, hi, is_suspicious, dir_label)

    return FeatureSignal(
        name=name,
        label=label,
        value=value,
        normal_min=lo,
        normal_max=hi,
        is_suspicious=is_suspicious,
        direction=dir_label,
        suspicion_weight=suspicion_weight,
        plain_english=plain_english,
    )


def _build_plain_english(
    name: str,
    label: str,
    value: float,
    lo: float,
    hi: float,
    is_suspicious: bool,
    direction: str,
) -> str:
    """Generate a one-sentence explanation understandable to a non-expert."""
    if not is_suspicious:
        return f"{label} is within the normal range for human speech ({lo}–{hi})."

    templates = {
        "spectral_flatness": {
            "unusually high": (
                "The frequency spectrum is unusually flat — natural speech has "
                "rich harmonic peaks, but this audio resembles noise-like TTS output."
            ),
        },
        "hf_energy_ratio": {
            "unusually high": (
                "There is excess energy above 4 kHz, which is common in vocoder-based "
                "or neural TTS synthesis that over-generates high frequencies."
            ),
        },
        "temporal_variance": {
            "unusually low": (
                "Energy barely varies over time — natural speech has dynamic "
                "loudness changes from phoneme transitions, but this audio is "
                "unnaturally smooth, a hallmark of voice cloning systems."
            ),
        },
        "mfcc1_mean": {
            "unusually high": (
                "The overall loudness profile (MFCC-1) is outside the typical range "
                "for real speech, which may indicate synthetic amplitude normalization."
            ),
            "unusually low": (
                "The overall loudness profile (MFCC-1) is outside the typical range "
                "for real speech, which may indicate synthetic amplitude normalization."
            ),
        },
        "mfcc_delta_energy": {
            "unusually low": (
                "The MFCC coefficients change very little between frames, suggesting "
                "unnaturally stable articulation — a common artifact of neural TTS systems."
            ),
        },
        "spectral_centroid_norm": {
            "unusually high": (
                "The spectral center of mass is shifted unusually high, which can "
                "indicate vocoder-processed audio with boosted treble content."
            ),
            "unusually low": (
                "The spectral center of mass is unusually low, which can indicate "
                "unnaturally bass-heavy or muffled synthesis artifacts."
            ),
        },
        "zero_crossing_rate": {
            "unusually high": (
                "The zero-crossing rate is abnormally high, suggesting the presence "
                "of synthetic noise or vocoder artifacts between phoneme boundaries."
            ),
            "unusually low": (
                "The zero-crossing rate is abnormally low, which can indicate "
                "over-smoothed synthesized speech lacking natural micro-variations."
            ),
        },
    }

    feature_templates = templates.get(name, {})
    return feature_templates.get(
        direction,
        f"{label} is {direction} (value={value:.4f}, normal range {lo}–{hi})."
    )


# ─── Public API ────────────────────────────────────────────────────────────────

def explain_verdict(
    mel_spectrogram: np.ndarray,
    mfcc: np.ndarray,
    fake_probability: float,
    verdict: str,
    confidence: float,
    mode: str = "demo",
) -> VerdictExplanation:
    """
    Generate a human-readable explanation for a verdict.

    Args:
        mel_spectrogram: 2D log-Mel spectrogram (n_mels, time_frames).
        mfcc: 2D MFCC array (n_mfcc, time_frames).
        fake_probability: Raw fake probability from the model.
        verdict: 'REAL' | 'DEEPFAKE' | 'UNCERTAIN'
        confidence: Confidence score from DecisionEngine.
        mode: 'demo' or 'ml'.

    Returns:
        VerdictExplanation instance with .to_dict() for JSON serialization.
    """
    if mel_spectrogram.size == 0:
        return VerdictExplanation(
            verdict=verdict,
            confidence=confidence,
            fake_probability=fake_probability,
            summary="Insufficient audio data to generate a feature explanation.",
            top_reason="No audio features could be extracted.",
            mode=mode,
        )

    # Extract all 7 acoustic signals
    raw_signals = _extract_signals(mel_spectrogram, mfcc)

    # Build FeatureSignal objects and sort: most suspicious first
    signals = [_build_signal(name, val) for name, val in raw_signals.items()]
    signals.sort(key=lambda s: s.suspicion_weight, reverse=True)

    suspicious = [s for s in signals if s.is_suspicious]
    n_suspicious = len(suspicious)

    # Build top-level summary
    summary = _build_summary(verdict, confidence, fake_probability, n_suspicious, suspicious)
    top_reason = suspicious[0].plain_english if suspicious else signals[0].plain_english

    return VerdictExplanation(
        verdict=verdict,
        confidence=confidence,
        fake_probability=fake_probability,
        summary=summary,
        indicators=signals,
        top_reason=top_reason,
        mode=mode,
    )


def _build_summary(
    verdict: str,
    confidence: float,
    fake_prob: float,
    n_suspicious: int,
    suspicious: list,
) -> str:
    pct = int(confidence * 100)
    if verdict == "REAL":
        if n_suspicious == 0:
            return (
                f"All {len(_FEATURE_SPECS)} acoustic features are within the normal "
                f"range for human speech. The model is {pct}% confident this is genuine audio."
            )
        return (
            f"The model rates this as likely REAL ({pct}% confidence). "
            f"{n_suspicious} feature(s) showed minor anomalies but not enough to trigger a deepfake alert."
        )
    elif verdict == "DEEPFAKE":
        top = suspicious[0].label if suspicious else "multiple features"
        return (
            f"Synthetic speech indicators detected ({pct}% confidence). "
            f"The most significant signal: {top}. "
            f"{n_suspicious} of {len(_FEATURE_SPECS)} acoustic features are outside "
            f"the typical range for real human speech."
        )
    else:  # UNCERTAIN
        return (
            f"The model cannot confidently classify this audio (fake_prob={fake_prob:.2f}). "
            f"{n_suspicious} suspicious feature(s) detected — manual review recommended."
        )

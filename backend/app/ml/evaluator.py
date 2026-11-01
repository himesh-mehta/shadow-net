"""
SHADOW-NET Evaluation Module (Phase 3)
======================================
Runs labeled audio files through the complete detection pipeline,
computes per-file verdicts, classifications, and aggregate metrics:
accuracy, precision, recall, F1-score, specificity, confusion matrix,
and latency.
"""

import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import get_settings
from app.audio.preprocessing import load_audio
from app.audio.vad import get_vad
from app.audio.features import slice_into_windows, extract_all_features
from app.ml.factory import get_detector
from app.ml.decision import DecisionEngine
from app.ml.explainer import explain_verdict

logger = logging.getLogger("shadow_net.evaluator")


def infer_ground_truth(filename: str) -> Optional[Dict[str, Any]]:
    """
    Determine ground truth from filename naming convention:
      - 'real_...'      -> REAL (label=0)
      - 'synthetic_...', 'fake_...', 'deepfake_...' -> DEEPFAKE (label=1)
    """
    lower = filename.lower()
    if lower.startswith("real_"):
        return {"label": 0, "name": "REAL"}
    if lower.startswith("synthetic_") or lower.startswith("fake_") or lower.startswith("deepfake_"):
        return {"label": 1, "name": "DEEPFAKE"}
    return None


def run_evaluation(
    audio_dir: Path,
    real_threshold: Optional[float] = None,
    deepfake_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run evaluation harness across all labeled WAV files in audio_dir.
    Returns structured evaluation results dictionary.
    """
    settings = get_settings()
    real_th = real_threshold if real_threshold is not None else settings.REAL_THRESHOLD
    fake_th = deepfake_threshold if deepfake_threshold is not None else settings.DEEPFAKE_THRESHOLD

    decision_engine = DecisionEngine(real_threshold=real_th, deepfake_threshold=fake_th)
    detector = get_detector()
    vad = get_vad()

    wav_files = sorted(audio_dir.glob("*.wav"))
    if not wav_files:
        raise ValueError(f"No .wav files found in directory: {audio_dir}")

    results = []
    tp = tn = fp = fn = 0
    uncertain_real = uncertain_fake = 0

    eval_start_time = time.perf_counter()

    for wav_path in wav_files:
        gt_info = infer_ground_truth(wav_path.name)
        if gt_info is None:
            logger.info("Skipping unlabeled file: %s", wav_path.name)
            continue

        gt_name = gt_info["name"]
        gt_label = gt_info["label"]

        t0 = time.perf_counter()

        with open(wav_path, "rb") as f:
            audio_bytes = f.read()

        audio, sr = load_audio(audio_bytes, target_sr=16000)
        duration_sec = round(len(audio) / sr, 2)

        # VAD filtering
        speech_audio, _, _ = vad.filter_speech(audio, sr=sr, sensitivity=settings.VAD_SENSITIVITY)
        active_audio = speech_audio if speech_audio.size > 0 else audio

        # Windowing
        windows = slice_into_windows(
            active_audio,
            sr=sr,
            window_sec=settings.AUDIO_WINDOW_SECONDS,
            hop_sec=settings.AUDIO_WINDOW_SECONDS / 2.0,
        )

        window_scores = []
        raw_windows_data = []

        if not windows:
            fake_prob = 0.5
            confidence = 0.5
            verdict = "UNCERTAIN"
            windows_count = 0
            explanation_dict = {"top_reason": "No speech windows detected in audio"}
        else:
            windows_count = len(windows)
            window_preds_for_agg = []

            for w in windows:
                feats = extract_all_features(w["audio"], sr=sr)
                pred = detector.predict_window(feats["mel_spectrogram"])
                fake_p = pred["fake_probability"]
                win_pred, win_threat, win_conf = decision_engine.evaluate_window(fake_p)
                window_preds_for_agg.append({
                    "fake_probability": fake_p,
                    "prediction": win_pred,
                    "threat_level": win_threat,
                    "confidence": win_conf,
                    "mel": feats["mel_spectrogram"],
                    "mfcc": feats["mfcc"],
                })

            session_eval = decision_engine.evaluate_session(window_preds_for_agg)
            raw_pred = session_eval["prediction"]
            verdict = raw_pred.value if hasattr(raw_pred, "value") else str(raw_pred)
            confidence = session_eval["confidence"]
            fake_prob = round(session_eval.get("average_fake_prob", 0.5), 4)

            # Pick representative features for explanation
            rep_w = min(
                window_preds_for_agg,
                key=lambda x: abs(x["fake_probability"] - fake_prob),
            )
            try:
                import numpy as _np
                explanation = explain_verdict(
                    mel_spectrogram=rep_w.get("mel", _np.zeros((128, 1), dtype="float32")),
                    mfcc=rep_w.get("mfcc", _np.zeros((20, 1), dtype="float32")),
                    fake_probability=fake_prob,
                    verdict=verdict,
                    confidence=confidence,
                    mode=detector.mode,
                )
                explanation_dict = explanation.to_dict()
            except Exception as e:
                logger.warning("Explainer error on %s: %s", wav_path.name, e)
                explanation_dict = {"top_reason": "Acoustic feature analysis"}

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        # Classification outcome mapping
        outcome = ""
        is_correct = False

        if gt_name == "DEEPFAKE":
            if verdict == "DEEPFAKE":
                outcome = "TP"
                is_correct = True
                tp += 1
            elif verdict == "REAL":
                outcome = "FN"
                is_correct = False
                fn += 1
            else:
                outcome = "UNCERTAIN_FAKE"
                uncertain_fake += 1
        elif gt_name == "REAL":
            if verdict == "REAL":
                outcome = "TN"
                is_correct = True
                tn += 1
            elif verdict == "DEEPFAKE":
                outcome = "FP"
                is_correct = False
                fp += 1
            else:
                outcome = "UNCERTAIN_REAL"
                uncertain_real += 1

        results.append({
            "filename": wav_path.name,
            "duration_sec": duration_sec,
            "windows_count": windows_count,
            "ground_truth": gt_name,
            "ground_truth_label": gt_label,
            "predicted_verdict": verdict,
            "fake_probability": fake_prob,
            "confidence": confidence,
            "outcome": outcome,
            "is_correct": is_correct,
            "latency_ms": latency_ms,
            "top_reason": explanation_dict.get("top_reason", ""),
            "explanation": explanation_dict,
        })

    total_time_sec = round(time.perf_counter() - eval_start_time, 2)
    total_evaluated = len(results)
    total_real = sum(1 for r in results if r["ground_truth"] == "REAL")
    total_fake = sum(1 for r in results if r["ground_truth"] == "DEEPFAKE")
    total_uncertain = uncertain_real + uncertain_fake
    decisive_total = tp + tn + fp + fn

    # Standard metrics
    strict_accuracy = round((tp + tn) / total_evaluated, 4) if total_evaluated > 0 else 0.0
    decisive_accuracy = round((tp + tn) / decisive_total, 4) if decisive_total > 0 else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    specificity = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0
    
    if (precision + recall) > 0:
        f1_score = round(2 * (precision * recall) / (precision + recall), 4)
    else:
        f1_score = 0.0

    uncertain_rate = round(total_uncertain / total_evaluated, 4) if total_evaluated > 0 else 0.0
    avg_latency_ms = round(sum(r["latency_ms"] for r in results) / total_evaluated, 1) if total_evaluated > 0 else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_directory": str(audio_dir),
        "thresholds": {
            "real_threshold": real_th,
            "deepfake_threshold": fake_th,
        },
        "summary": {
            "total_files": total_evaluated,
            "total_real": total_real,
            "total_fake": total_fake,
            "strict_accuracy": strict_accuracy,
            "decisive_accuracy": decisive_accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "f1_score": f1_score,
            "uncertain_rate": uncertain_rate,
            "average_latency_ms": avg_latency_ms,
            "total_processing_time_sec": total_time_sec,
        },
        "confusion_matrix": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "uncertain_real": uncertain_real,
            "uncertain_fake": uncertain_fake,
            "total_uncertain": total_uncertain,
        },
        "per_file_results": results,
    }

    return report

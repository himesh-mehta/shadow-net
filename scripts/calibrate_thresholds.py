#!/usr/bin/env python3
"""
SHADOW-NET — Threshold Calibration Script (Phase 1, Item 2)
===========================================================
Runs labeled validation audio through the full detection pipeline,
computes an ROC curve, Equal Error Rate (EER), and suggests calibrated
REAL_THRESHOLD / DEEPFAKE_THRESHOLD values to write back to .env.

Usage
-----
  # From the project root:
  python scripts/calibrate_thresholds.py --audio-dir datasets/sample

  # With a custom audio directory containing labeled WAV files:
  python scripts/calibrate_thresholds.py --audio-dir /path/to/labeled_audio

  # Write suggested thresholds directly into .env:
  python scripts/calibrate_thresholds.py --audio-dir datasets/sample --update-env

Label Convention
----------------
  Filenames starting with "real_"      → ground-truth REAL  (label = 0)
  Filenames starting with "synthetic_" → ground-truth FAKE  (label = 1)
  Files with neither prefix are skipped with a warning.

Output
------
  - Prints an ASCII ROC curve + EER + suggested thresholds to stdout
  - Writes a machine-readable JSON report to:
      scripts/calibration_report.json
  - Optionally patches REAL_THRESHOLD / DEEPFAKE_THRESHOLD in .env
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any

# ── Make sure backend package is importable when run from project root ─────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("calibrate")


# ── Helpers ────────────────────────────────────────────────────────────────────

def infer_label_from_filename(filename: str) -> int | None:
    """Return 1 (fake) or 0 (real) based on filename prefix, or None to skip."""
    name = filename.lower()
    if name.startswith("real_"):
        return 0
    if name.startswith("synthetic_") or name.startswith("fake_") or name.startswith("deepfake_"):
        return 1
    return None


def run_pipeline_on_file(wav_path: Path) -> float:
    """
    Run the full SHADOW-NET audio pipeline on a WAV file and return the
    aggregated fake_probability score (the same metric the DecisionEngine sees).
    """
    from app.audio.preprocessing import load_audio
    from app.audio.vad import get_vad
    from app.audio.features import slice_into_windows, extract_all_features
    from app.ml.factory import get_detector

    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    audio, sr = load_audio(audio_bytes, target_sr=16000)

    vad = get_vad()
    speech_audio, _, _ = vad.filter_speech(audio, sr=sr, sensitivity=2)
    active_audio = speech_audio if speech_audio.size > 0 else audio

    windows = slice_into_windows(active_audio, sr=sr, window_sec=2.0, hop_sec=1.0)
    if not windows:
        logger.warning(f"  No windows extracted from {wav_path.name} — assigning 0.5")
        return 0.5

    detector = get_detector()
    fake_probs = []
    for w in windows:
        feats = extract_all_features(w["audio"], sr=sr)
        pred = detector.predict_window(feats["mel_spectrogram"])
        fake_probs.append(pred["fake_probability"])

    # Replicate the same aggregation used in DecisionEngine.evaluate_session()
    avg_fake = sum(fake_probs) / len(fake_probs)
    max_fake = max(fake_probs)
    aggregated = 0.60 * max_fake + 0.40 * avg_fake
    return round(aggregated, 4)


def compute_roc(
    labels: List[int], scores: List[float], n_thresholds: int = 200
) -> Tuple[List[float], List[float], List[float]]:
    """
    Compute ROC curve points (FPR, TPR) across n_thresholds evenly spaced
    between 0.0 and 1.0.

    Returns (fpr_list, tpr_list, threshold_list).
    """
    thresholds = [i / n_thresholds for i in range(n_thresholds + 1)]
    fpr_list, tpr_list = [], []

    total_pos = sum(labels)
    total_neg = len(labels) - total_pos

    for th in thresholds:
        tp = sum(1 for l, s in zip(labels, scores) if l == 1 and s >= th)
        fp = sum(1 for l, s in zip(labels, scores) if l == 0 and s >= th)
        tpr = tp / total_pos if total_pos > 0 else 0.0
        fpr = fp / total_neg if total_neg > 0 else 0.0
        fpr_list.append(round(fpr, 4))
        tpr_list.append(round(tpr, 4))

    return fpr_list, tpr_list, thresholds


def compute_auc(fpr_list: List[float], tpr_list: List[float]) -> float:
    """Trapezoidal AUC from ROC lists (both sorted descending by threshold)."""
    auc = 0.0
    for i in range(1, len(fpr_list)):
        dx = abs(fpr_list[i - 1] - fpr_list[i])
        auc += dx * (tpr_list[i - 1] + tpr_list[i]) / 2.0
    return round(auc, 4)


def find_eer(
    fpr_list: List[float], tpr_list: List[float], thresholds: List[float]
) -> Tuple[float, float]:
    """
    Find Equal Error Rate: the threshold where FPR ≈ FNR (1 - TPR).
    Returns (eer_value, eer_threshold).
    """
    best_diff = float("inf")
    eer_val, eer_th = 0.5, 0.5

    for fpr, tpr, th in zip(fpr_list, tpr_list, thresholds):
        fnr = 1.0 - tpr
        diff = abs(fpr - fnr)
        if diff < best_diff:
            best_diff = diff
            eer_val = round((fpr + fnr) / 2.0, 4)
            eer_th = round(th, 4)

    return eer_val, eer_th


def find_youden_threshold(
    fpr_list: List[float], tpr_list: List[float], thresholds: List[float]
) -> Tuple[float, float, float]:
    """
    Youden's J statistic: maximize (TPR - FPR).
    Returns (best_threshold, tpr_at_best, fpr_at_best).
    """
    best_j, best_th, best_tpr, best_fpr = -1.0, 0.5, 0.0, 1.0
    for fpr, tpr, th in zip(fpr_list, tpr_list, thresholds):
        j = tpr - fpr
        if j > best_j:
            best_j = j
            best_th = round(th, 4)
            best_tpr = round(tpr, 4)
            best_fpr = round(fpr, 4)
    return best_th, best_tpr, best_fpr


def render_ascii_roc(
    fpr_list: List[float], tpr_list: List[float], width: int = 60, height: int = 20
) -> str:
    """Render an ASCII ROC curve plot."""
    grid = [["·"] * width for _ in range(height)]

    # Plot diagonal (random classifier)
    for i in range(min(width, height)):
        x = int(i / height * width)
        y = height - 1 - i
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = "·"

    # Plot ROC curve
    for fpr, tpr in zip(fpr_list, tpr_list):
        x = int(fpr * (width - 1))
        y = height - 1 - int(tpr * (height - 1))
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = "█"

    lines = []
    lines.append("  TPR")
    lines.append("  1.0 ┤" + "".join(grid[0]))
    for i, row in enumerate(grid[1:], 1):
        prefix = "      │" if i < height - 1 else "  0.0 ┤"
        lines.append(prefix + "".join(row))
    lines.append("       └" + "─" * width)
    lines.append("       0.0" + " " * (width - 10) + "FPR  1.0")
    return "\n".join(lines)


def suggest_thresholds(eer_th: float, youden_th: float) -> Tuple[float, float]:
    """
    Derive calibrated REAL_THRESHOLD and DEEPFAKE_THRESHOLD.

    Strategy:
    - Use the average of EER and Youden thresholds as the DEEPFAKE cutoff.
    - Set the REAL_THRESHOLD conservatively lower (DEEPFAKE_TH - 0.30),
      clamped to sensible bounds [0.10, 0.55].
    """
    deepfake_th = round((eer_th + youden_th) / 2.0, 2)
    deepfake_th = max(0.50, min(0.95, deepfake_th))
    real_th = round(deepfake_th - 0.30, 2)
    real_th = max(0.10, min(0.55, real_th))
    return real_th, deepfake_th


def patch_env_file(env_path: Path, real_th: float, deepfake_th: float) -> None:
    """Write or update REAL_THRESHOLD / DEEPFAKE_THRESHOLD in .env."""
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []

    updated = {"REAL_THRESHOLD": False, "DEEPFAKE_THRESHOLD": False}
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("REAL_THRESHOLD="):
            new_lines.append(f"REAL_THRESHOLD={real_th}")
            updated["REAL_THRESHOLD"] = True
        elif stripped.startswith("DEEPFAKE_THRESHOLD="):
            new_lines.append(f"DEEPFAKE_THRESHOLD={deepfake_th}")
            updated["DEEPFAKE_THRESHOLD"] = True
        else:
            new_lines.append(line)

    if not updated["REAL_THRESHOLD"]:
        new_lines.append(f"REAL_THRESHOLD={real_th}")
    if not updated["DEEPFAKE_THRESHOLD"]:
        new_lines.append(f"DEEPFAKE_THRESHOLD={deepfake_th}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(f"✅  .env updated: REAL_THRESHOLD={real_th}, DEEPFAKE_THRESHOLD={deepfake_th}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SHADOW-NET threshold calibration — ROC curve + EER analysis"
    )
    parser.add_argument(
        "--audio-dir",
        default="datasets/sample",
        help="Directory containing labeled WAV files (real_*.wav / synthetic_*.wav)",
    )
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="Patch REAL_THRESHOLD / DEEPFAKE_THRESHOLD in .env after calibration",
    )
    parser.add_argument(
        "--output",
        default="scripts/calibration_report.json",
        help="Path to write the JSON calibration report",
    )
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir)
    if not audio_dir.exists():
        logger.error(f"Audio directory not found: {audio_dir}")
        sys.exit(1)

    wav_files = sorted(audio_dir.glob("*.wav"))
    if not wav_files:
        logger.error(f"No .wav files found in {audio_dir}")
        sys.exit(1)

    print("\n" + "═" * 64)
    print("  SHADOW-NET — THRESHOLD CALIBRATION  (Phase 1 · Item 2)")
    print("═" * 64)

    # ── Step 1: Run pipeline on all labeled files ───────────────────────────
    labels: List[int] = []
    scores: List[float] = []
    file_results: List[Dict[str, Any]] = []

    print(f"\n📂  Scanning {audio_dir} for labeled WAV files...\n")
    for wav in wav_files:
        label = infer_label_from_filename(wav.name)
        if label is None:
            logger.warning(f"  ⚠  Skipping '{wav.name}' — no real_/synthetic_ prefix")
            continue

        label_str = "REAL (0)" if label == 0 else "FAKE (1)"
        logger.info(f"  🎙  {wav.name}  [{label_str}]")

        t0 = time.perf_counter()
        try:
            score = run_pipeline_on_file(wav)
        except Exception as e:
            logger.error(f"  ✗  Pipeline failed on {wav.name}: {e}")
            continue
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        labels.append(label)
        scores.append(score)
        file_results.append({
            "file": wav.name,
            "ground_truth": label,
            "fake_probability": score,
            "latency_ms": latency_ms,
        })
        logger.info(f"     fake_prob={score:.4f}  latency={latency_ms}ms")

    if len(labels) < 2:
        logger.error("Need at least 2 labeled files (1 real + 1 fake). Aborting.")
        sys.exit(1)

    n_real = labels.count(0)
    n_fake = labels.count(1)
    print(f"\n  Files processed: {len(labels)}  (real={n_real}, fake={n_fake})")

    # ── Step 2: ROC curve ───────────────────────────────────────────────────
    fpr_list, tpr_list, thresholds = compute_roc(labels, scores)
    auc = compute_auc(fpr_list, tpr_list)
    eer_val, eer_th = find_eer(fpr_list, tpr_list, thresholds)
    youden_th, youden_tpr, youden_fpr = find_youden_threshold(fpr_list, tpr_list, thresholds)

    # ── Step 3: Suggest calibrated thresholds ──────────────────────────────
    real_th, deepfake_th = suggest_thresholds(eer_th, youden_th)

    # ── Step 4: Print report ────────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("  ROC CURVE")
    print("─" * 64)
    print(render_ascii_roc(fpr_list, tpr_list))

    print("\n" + "─" * 64)
    print("  METRICS")
    print("─" * 64)
    print(f"  AUC (area under ROC)      : {auc:.4f}  {'✅ Good' if auc >= 0.80 else '⚠ Below 0.80 — retrain?'}")
    print(f"  EER (equal error rate)    : {eer_val:.4f}  at threshold {eer_th}")
    print(f"  Youden optimum threshold  : {youden_th}  (TPR={youden_tpr}, FPR={youden_fpr})")

    print("\n" + "─" * 64)
    print("  SUGGESTED THRESHOLDS")
    print("─" * 64)
    print(f"  REAL_THRESHOLD      = {real_th}")
    print(f"  DEEPFAKE_THRESHOLD  = {deepfake_th}")
    print(f"\n  Verdict zones:")
    print(f"    fake_prob < {real_th}          → REAL")
    print(f"    {real_th} ≤ fake_prob < {deepfake_th}  → UNCERTAIN")
    print(f"    fake_prob ≥ {deepfake_th}         → DEEPFAKE")

    if n_real < 5 or n_fake < 5:
        print("\n  ⚠  WARNING: Small validation set (<5 files per class).")
        print("     These suggestions are indicative only. Validate on a larger")
        print("     dataset (e.g. ASVspoof LA eval partition) before deploying.")

    # ── Step 5: Write JSON report ───────────────────────────────────────────
    report = {
        "calibration_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "audio_dir": str(audio_dir.resolve()),
        "n_files": len(labels),
        "n_real": n_real,
        "n_fake": n_fake,
        "auc": auc,
        "eer": eer_val,
        "eer_threshold": eer_th,
        "youden_threshold": youden_th,
        "youden_tpr": youden_tpr,
        "youden_fpr": youden_fpr,
        "suggested_real_threshold": real_th,
        "suggested_deepfake_threshold": deepfake_th,
        "file_results": file_results,
        "roc": {
            "fpr": fpr_list[::5],   # Subsample to keep report compact
            "tpr": tpr_list[::5],
            "thresholds": thresholds[::5],
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  📄  JSON report written to: {output_path}")

    # ── Step 6: Optionally patch .env ───────────────────────────────────────
    if args.update_env:
        env_path = PROJECT_ROOT / ".env"
        patch_env_file(env_path, real_th, deepfake_th)
        print(f"\n  ✅  .env patched. Restart the backend to apply new thresholds.")
        print(f"      (uvicorn main:app --reload --port 8000)")

    print("\n" + "═" * 64 + "\n")


if __name__ == "__main__":
    main()

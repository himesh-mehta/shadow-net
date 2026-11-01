#!/usr/bin/env python3
"""
SHADOW-NET — Model Evaluation Harness (Phase 3)
==============================================
Runs the full detection pipeline across labeled audio files, reports
per-file verdicts against ground truth, computes aggregate metrics
(Accuracy, Precision, Recall, F1, Specificity, Confusion Matrix, Latency),
and outputs both an ASCII terminal report and a structured JSON report.

Usage
-----
  # Default run on sample dataset using configured .env thresholds:
  python scripts/evaluate.py

  # Specify a custom audio directory:
  python scripts/evaluate.py --audio-dir datasets/sample

  # Test custom threshold cutoffs (what-if analysis):
  python scripts/evaluate.py --real-th 0.30 --fake-th 0.70

  # Compare calibrated thresholds against a naive 0.50 cutoff:
  python scripts/evaluate.py --compare

  # Custom output path:
  python scripts/evaluate.py --output scripts/evaluation_report.json
"""

import sys
import json
import argparse
from pathlib import Path

# ── Ensure backend is importable ───────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import get_settings
from app.ml.evaluator import run_evaluation


def print_banner(title: str, width: int = 76):
    print("=" * width)
    print(f"  {title}".center(width))
    print("=" * width)


def render_ascii_report(report: dict):
    summary = report["summary"]
    cm = report["confusion_matrix"]
    thresholds = report["thresholds"]
    files = report["per_file_results"]

    print_banner("SHADOW-NET MODEL EVALUATION HARNESS")
    print(f" Dataset Directory : {report['dataset_directory']}")
    print(f" Real Threshold    : < {thresholds['real_threshold']:.2f}  (Predicted as REAL)")
    print(f" Deepfake Threshold: >= {thresholds['deepfake_threshold']:.2f} (Predicted as DEEPFAKE)")
    print(f" Uncertain Band    : [{thresholds['real_threshold']:.2f}, {thresholds['deepfake_threshold']:.2f}) (Flagged for Review)")
    print("-" * 76)

    # Per-file table
    print("\n[1] PER-FILE EVALUATION BREAKDOWN")
    print("-" * 76)
    header = f"{'#':<3} {'File Name':<32} {'Truth':<10} {'Fake Prob':<10} {'Verdict':<10} {'Match':<8} {'Latency'}"
    print(header)
    print("-" * 76)

    for i, item in enumerate(files, 1):
        status_tag = "PASS" if item["is_correct"] else ("AMBER" if "UNCERTAIN" in item["outcome"] else "FAIL")
        # shorten file name if needed
        fname = item["filename"]
        if len(fname) > 30:
            fname = fname[:27] + "..."
        row = (
            f"{i:<3} "
            f"{fname:<32} "
            f"{item['ground_truth']:<10} "
            f"{item['fake_probability']:<10.4f} "
            f"{item['predicted_verdict']:<10} "
            f"{status_tag:<8} "
            f"{item['latency_ms']}ms"
        )
        print(row)

    print("-" * 76)

    # Top reasons per file
    print("\n[2] ACOUSTIC EXPLANATIONS (WHY)")
    print("-" * 76)
    for i, item in enumerate(files, 1):
        print(f"  {i}. {item['filename']}")
        print(f"     Verdict: {item['predicted_verdict']} | Top Reason: {item['top_reason']}")
    print("-" * 76)

    # Confusion matrix
    print("\n[3] CONFUSION MATRIX")
    print("-" * 76)
    print("                      Actual DEEPFAKE         Actual REAL")
    print(f"  Predicted DEEPFAKE  TP = {cm['true_positives']:<18} FP = {cm['false_positives']}")
    print(f"  Predicted REAL      FN = {cm['false_negatives']:<18} TN = {cm['true_negatives']}")
    print(f"  UNCERTAIN (review)  Uncertain Fake = {cm['uncertain_fake']:<10} Uncertain Real = {cm['uncertain_real']}")
    print(f"  Total Indeterminate: {cm['total_uncertain']} / {summary['total_files']} samples")
    print("-" * 76)

    # Summary performance metrics
    print("\n[4] AGGREGATE PERFORMANCE METRICS")
    print("-" * 76)
    print(f"  Total Audio Files Tested : {summary['total_files']} ({summary['total_fake']} Deepfake, {summary['total_real']} Real)")
    print(f"  Strict Accuracy          : {summary['strict_accuracy'] * 100:.1f}%")
    print(f"  Decisive Accuracy        : {summary['decisive_accuracy'] * 100:.1f}% (excluding uncertain)")
    print(f"  Precision                : {summary['precision'] * 100:.1f}%")
    print(f"  Recall (Sensitivity)     : {summary['recall'] * 100:.1f}%")
    print(f"  Specificity              : {summary['specificity'] * 100:.1f}%")
    print(f"  F1-Score                 : {summary['f1_score']:.4f}")
    print(f"  Uncertain Rate           : {summary['uncertain_rate'] * 100:.1f}%")
    print(f"  Average Pipeline Latency : {summary['average_latency_ms']:.1f} ms")
    print(f"  Total Test Bench Time    : {summary['total_processing_time_sec']:.2f} s")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="SHADOW-NET Evaluation Harness")
    parser.add_argument(
        "--audio-dir",
        type=str,
        default=str(PROJECT_ROOT / "datasets" / "sample"),
        help="Path to directory containing labeled WAV files (default: datasets/sample)",
    )
    parser.add_argument(
        "--real-th",
        type=float,
        default=None,
        help="Custom REAL threshold cutoff (default: from config/settings)",
    )
    parser.add_argument(
        "--fake-th",
        type=float,
        default=None,
        help="Custom DEEPFAKE threshold cutoff (default: from config/settings)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(SCRIPT_DIR / "evaluation_report.json"),
        help="Path to write JSON evaluation report (default: scripts/evaluation_report.json)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare current calibrated thresholds against naive 0.50 binary threshold",
    )

    args = parser.parse_args()
    audio_path = Path(args.audio_dir)

    if not audio_path.exists() or not audio_path.is_dir():
        print(f"[ERROR] Audio directory not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Running SHADOW-NET evaluation on {audio_path}...")
    report = run_evaluation(
        audio_dir=audio_path,
        real_threshold=args.real_th,
        deepfake_threshold=args.fake_th,
    )

    render_ascii_report(report)

    # Write report to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[INFO] Structured evaluation report written to: {output_path}")

    # Optional naive threshold comparison
    if args.compare:
        print("\n" + "=" * 76)
        print("  COMPARISON: CALIBRATED THRESHOLDS vs NAIVE SINGLE THRESHOLD (0.50)")
        print("=" * 76)
        naive_report = run_evaluation(
            audio_dir=audio_path,
            real_threshold=0.50,
            deepfake_threshold=0.50,
        )
        print(f"{'Metric':<25} {'Calibrated Scheme':<22} {'Naive Cutoff (0.50)'}")
        print("-" * 76)
        print(f"{'Thresholds':<25} {str(report['thresholds']):<22} {{'cutoff': 0.50}}")
        print(f"{'Strict Accuracy':<25} {report['summary']['strict_accuracy']*100:.1f}%{'':<16} {naive_report['summary']['strict_accuracy']*100:.1f}%")
        print(f"{'Precision':<25} {report['summary']['precision']*100:.1f}%{'':<16} {naive_report['summary']['precision']*100:.1f}%")
        print(f"{'Recall':<25} {report['summary']['recall']*100:.1f}%{'':<16} {naive_report['summary']['recall']*100:.1f}%")
        print(f"{'F1 Score':<25} {report['summary']['f1_score']:<22.4f} {naive_report['summary']['f1_score']:.4f}")
        print(f"{'Uncertain Samples':<25} {report['confusion_matrix']['total_uncertain']:<22} {naive_report['confusion_matrix']['total_uncertain']}")
        print("=" * 76)


if __name__ == "__main__":
    main()

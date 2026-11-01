"""Evaluate your own labeled speech WAV files; never substitutes repository samples."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml.factory import get_detector
from app.ml.evaluator import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="Evaluate real_*.wav and fake_*.wav using the pretrained detector.")
    parser.add_argument("audio_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/my-recordings.json"))
    args = parser.parse_args()
    detector = get_detector(demo_mode=False)
    report = run_evaluation(args.audio_dir, detector=detector)
    if report["summary"]["total_files"] == 0:
        parser.error("No labeled files. Name WAVs real_*.wav and fake_*.wav; labels are used for scoring only.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Saved {args.output}. Report errors and uncertain results; do not select only successful examples.")


if __name__ == "__main__": main()

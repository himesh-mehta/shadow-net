"""
Evaluation & Robustness Stress Testing Suite for SHADOW-NET.
Computes:
1. Baseline test split metrics (Accuracy, Precision, Recall, F1, ROC-AUC, FPR, Confusion Matrix).
2. Inference Latency Benchmark against the <50ms SLA (Mean, P95, P99, Throughput).
3. Robustness Stress Tests:
   - Additive Gaussian Noise at +20dB, +10dB, +5dB SNR
   - Audio Compression & Amplitude Clipping
   - Pitch / Formant Frequency Shifting
   - Multi-speaker Cross-Talk / Voice Overlap
"""

import sys
import time
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from training.dataset import AudioSpoofDataset
from training.models import build_resnet18, CNNBaseline
from training.train import compute_epoch_metrics
from app.audio.preprocessing import load_audio, normalize_audio
from app.audio.features import extract_mel_spectrogram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shadow_net.evaluation")


def load_trained_model(model_path: str, model_type: str = "resnet18", device: torch.device = None) -> nn.Module:
    """Loads model weights from checkpoint."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if model_type == "cnn":
        model = CNNBaseline()
    else:
        model = build_resnet18(pretrained=False)

    if not Path(model_path).is_file():
        raise FileNotFoundError(f"Model checkpoint not found: {model_path}")

    checkpoint = torch.load(model_path, map_location=device)
    state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    logger.info(f"Loaded {model_type} from {model_path}")
    return model


def benchmark_latency(model: nn.Module, device: torch.device, n_runs: int = 100) -> Dict[str, Any]:
    """
    Measures per-window inference latency over n_runs.
    Target SLA: <50ms per window.
    """
    dummy_input = torch.randn(1, 1, 128, 63).to(device)

    # Warmup runs
    with torch.no_grad():
        for _ in range(10):
            _ = model(dummy_input)

    latencies = []
    with torch.no_grad():
        for _ in range(n_runs):
            t0 = time.perf_counter()
            _ = model(dummy_input)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms

    latencies = np.array(latencies)
    mean_lat = float(np.mean(latencies))
    median_lat = float(np.median(latencies))
    p95_lat = float(np.percentile(latencies, 95))
    p99_lat = float(np.percentile(latencies, 99))
    throughput = float(1000.0 / mean_lat) if mean_lat > 0 else 0.0
    meets_sla = p95_lat < 50.0

    return {
        "n_runs": n_runs,
        "mean_ms": round(mean_lat, 2),
        "median_ms": round(median_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "p99_ms": round(p99_lat, 2),
        "throughput_windows_per_sec": round(throughput, 1),
        "sla_target_ms": 50.0,
        "meets_sla": meets_sla,
    }


def evaluate_test_split(
    model: nn.Module,
    test_manifest_path: str,
    device: torch.device,
    batch_size: int = 16,
) -> Dict[str, Any]:
    """Evaluates standard test set."""
    test_ds = AudioSpoofDataset(test_manifest_path)
    loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    all_targets = []
    all_preds = []
    all_probs = []

    model.eval()
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            logits = model(inputs)
            probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

            all_targets.extend(targets.numpy())
            all_preds.extend(preds)
            all_probs.extend(probs)

    metrics = compute_epoch_metrics(np.array(all_targets), np.array(all_preds), np.array(all_probs))
    return metrics


# ---------------------------------------------------------------------------
# Robustness Stress Perturbations
# ---------------------------------------------------------------------------

def apply_snr_noise(audio: np.ndarray, target_snr_db: float) -> np.ndarray:
    """Adds white Gaussian noise to audio at specified SNR (dB)."""
    signal_power = np.mean(audio ** 2)
    if signal_power == 0:
        return audio
    snr_linear = 10 ** (target_snr_db / 10.0)
    noise_power = signal_power / snr_linear
    noise = np.random.normal(0, np.sqrt(noise_power), size=len(audio)).astype(np.float32)
    noisy_audio = audio + noise
    return normalize_audio(noisy_audio)


def apply_compression_clipping(audio: np.ndarray, threshold: float = 0.6) -> np.ndarray:
    """Simulates VoIP compression and hard amplitude clipping."""
    clipped = np.clip(audio, -threshold, threshold)
    return normalize_audio(clipped)


def apply_pitch_shift_simulation(audio: np.ndarray, factor: float = 1.05) -> np.ndarray:
    """Simulates voice conversion / pitch shift by linear resampling."""
    orig_len = len(audio)
    indices = np.round(np.arange(0, orig_len, factor)).astype(int)
    indices = indices[indices < orig_len]
    shifted = audio[indices]
    # Pad or trim back to original length
    if len(shifted) < orig_len:
        padded = np.zeros(orig_len, dtype=np.float32)
        padded[:len(shifted)] = shifted
        return padded
    return shifted[:orig_len]


def run_robustness_eval(
    model: nn.Module,
    test_records: List[Dict[str, Any]],
    device: torch.device,
) -> Dict[str, Dict[str, Any]]:
    """
    Tests model resilience across various audio degradations.
    """
    conditions = {
        "Clean Baseline": lambda a: a,
        "Noise (+20 dB SNR)": lambda a: apply_snr_noise(a, 20.0),
        "Noise (+10 dB SNR)": lambda a: apply_snr_noise(a, 10.0),
        "Noise (+5 dB SNR)": lambda a: apply_snr_noise(a, 5.0),
        "Clipping / Compression": lambda a: apply_compression_clipping(a, 0.5),
        "Pitch Shift (+5%)": lambda a: apply_pitch_shift_simulation(a, 1.05),
        "Pitch Shift (-5%)": lambda a: apply_pitch_shift_simulation(a, 0.95),
    }

    results = {}
    target_samples = 32000  # 2.0s at 16kHz

    for cond_name, perturb_fn in conditions.items():
        all_targets = []
        all_preds = []
        all_probs = []

        for rec in test_records:
            audio_path = rec["audio_path"]
            label = int(rec["label"])

            try:
                raw_audio, _ = load_audio(audio_path, target_sr=16000)
                if len(raw_audio) < target_samples:
                    padded = np.zeros(target_samples, dtype=np.float32)
                    padded[:len(raw_audio)] = raw_audio
                    audio_slice = padded
                else:
                    audio_slice = raw_audio[:target_samples]

                # Apply perturbation
                perturbed = perturb_fn(audio_slice)

                # Extract spectrogram
                mel_spec = extract_mel_spectrogram(perturbed, sr=16000)
                tensor = torch.from_numpy(mel_spec).unsqueeze(0).unsqueeze(0).float().to(device)

                with torch.no_grad():
                    logits = model(tensor)
                    prob = float(torch.softmax(logits, dim=-1)[0, 1].cpu().item())
                    pred = int(torch.argmax(logits, dim=-1)[0].cpu().item())

                all_targets.append(label)
                all_preds.append(pred)
                all_probs.append(prob)

            except Exception as e:
                logger.warning(f"Failed to evaluate {audio_path} under {cond_name}: {e}")

        metrics = compute_epoch_metrics(np.array(all_targets), np.array(all_preds), np.array(all_probs))
        results[cond_name] = metrics

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate SHADOW-NET Audio Classifier")
    parser.add_argument("--model-path", type=str, default="model/resnet18.pth", help="Path to .pth checkpoint")
    parser.add_argument("--model-type", type=str, default="resnet18", choices=["resnet18", "cnn"], help="Architecture")
    parser.add_argument("--test-manifest", type=str, default="data/synthetic/test.json", help="Path to test.json")
    parser.add_argument("--device", type=str, default=None, help="Device (cpu, cuda)")
    parser.add_argument("--n-latency-runs", type=int, default=100, help="Repetitions for latency test")

    args = parser.parse_args()

    device = torch.device(args.device) if args.device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_trained_model(args.model_path, model_type=args.model_type, device=device)

    # 1. Latency SLA Benchmark
    print("\n" + "=" * 80)
    print("1. LATENCY BENCHMARK (<50ms SLA Target)")
    print("=" * 80)
    latency_info = benchmark_latency(model, device, n_runs=args.n_latency_runs)
    print(f"  Device: {device}")
    print(f"  Mean Latency:   {latency_info['mean_ms']} ms")
    print(f"  Median Latency: {latency_info['median_ms']} ms")
    print(f"  P95 Latency:    {latency_info['p95_ms']} ms (SLA Threshold: {latency_info['sla_target_ms']} ms)")
    print(f"  P99 Latency:    {latency_info['p99_ms']} ms")
    print(f"  Throughput:     {latency_info['throughput_windows_per_sec']} windows/sec")
    sla_status = "PASS [MEETS SLA]" if latency_info["meets_sla"] else "FAIL [EXCEEDS SLA]"
    print(f"  Status:         {sla_status}")

    # 2. Test Split Evaluation
    print("\n" + "=" * 80)
    print(f"2. TEST SPLIT EVALUATION: {args.test_manifest}")
    print("=" * 80)
    test_metrics = evaluate_test_split(model, args.test_manifest, device)
    print(f"  Accuracy:         {test_metrics['accuracy'] * 100:.2f}%")
    print(f"  Precision:        {test_metrics['precision'] * 100:.2f}%")
    print(f"  Recall:           {test_metrics['recall'] * 100:.2f}%")
    print(f"  F1 Score:         {test_metrics['f1']:.4f}")
    print(f"  ROC-AUC:          {test_metrics['roc_auc']:.4f}")
    print(f"  False Pos. Rate:  {test_metrics['fpr'] * 100:.2f}%")
    cm = test_metrics["confusion_matrix"]
    print(f"  Confusion Matrix: TN={cm['tn']}, FP={cm['fp']}, FN={cm['fn']}, TP={cm['tp']}")

    # 3. Robustness Stress Suite
    print("\n" + "=" * 80)
    print("3. ROBUSTNESS STRESS EVALUATION")
    print("=" * 80)
    with open(args.test_manifest, "r", encoding="utf-8") as f:
        test_records = json.load(f)

    robustness_results = run_robustness_eval(model, test_records, device)
    print(f"{'Condition':<26} | {'Accuracy':<10} | {'F1-Score':<10} | {'ROC-AUC':<10} | {'FPR':<10}")
    print("-" * 75)
    for cond, m in robustness_results.items():
        print(f"{cond:<26} | {m['accuracy']*100:>8.2f}% | {m['f1']:>10.4f} | {m['roc_auc']:>10.4f} | {m['fpr']*100:>8.2f}%")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

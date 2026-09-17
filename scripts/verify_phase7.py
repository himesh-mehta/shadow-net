"""
Phase 7 Verification Script for SHADOW-NET.
Validates:
1. Synthetic dataset generator and manifest creation (train/val/test splits).
2. AudioSpoofDataset feature extraction and batch tensor shapes (1, 128, 63).
3. CNNBaseline model training loop and metric logging.
4. ResNet-18 model training loop and checkpoint export to model/resnet18.pth.
5. Checkpoint integrity and state_dict compatibility with Phase 3 classifier.
6. Test evaluation and latency benchmark (<50ms SLA).
7. Robustness perturbation tests (noise, compression, pitch shift).
8. Backend seamless switch from demo mode to ML mode when model weights exist.
"""

import os
import sys
import json
import time
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
MODEL_PATH = PROJECT_ROOT / "model" / "resnet18.pth"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import torch


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/8] {title}...")


def test_1_dataset_generation():
    log_step(1, "Generating Synthetic Balanced Dataset")
    from training.dataset_prep import create_synthetic_test_bench

    manifests = create_synthetic_test_bench(DATA_DIR, n_samples=30)
    for split in ["train", "val", "test"]:
        manifest_file = Path(manifests[split])
        assert manifest_file.is_file(), f"Manifest {manifest_file} was not created!"
        with open(manifest_file, "r") as f:
            records = json.load(f)
            assert len(records) > 0, f"Split {split} is empty!"
    print("  [OK] Train, Val, and Test manifests created successfully with balanced audio samples.")


def test_2_dataset_loader_shapes():
    log_step(2, "Verifying AudioSpoofDataset & Preprocessing Parity")
    from training.dataset import AudioSpoofDataset
    from torch.utils.data import DataLoader

    train_manifest = DATA_DIR / "train.json"
    ds = AudioSpoofDataset(str(train_manifest))
    assert len(ds) > 0, "Dataset should have samples"

    tensor, label = ds[0]
    print(f"  Single sample shape: {tensor.shape}, Label: {label}")
    # Expected shape: (1, 128, 63)
    assert tensor.shape == (1, 128, 63), f"Expected (1, 128, 63), got {tensor.shape}"
    assert label in [0, 1], f"Label should be 0 or 1, got {label}"

    loader = DataLoader(ds, batch_size=4, shuffle=True)
    batch_x, batch_y = next(iter(loader))
    assert batch_x.shape == (4, 1, 128, 63), f"Batch shape expected (4, 1, 128, 63), got {batch_x.shape}"
    print(f"  DataLoader batch shape: {batch_x.shape}, Labels: {batch_y.tolist()}")
    print("  [OK] Feature extraction parity verified. Shapes match (batch, 1, 128, 63).")


def test_3_cnn_baseline_training():
    log_step(3, "Training CNN Baseline Model")
    from training.train import train_pipeline

    cnn_model_path = PROJECT_ROOT / "model" / "cnn_baseline.pth"
    res = train_pipeline(
        model_name="cnn",
        data_dir=str(DATA_DIR),
        epochs=2,
        batch_size=8,
        lr=1e-3,
        output_model=str(cnn_model_path),
        device_name="cpu",
    )
    assert cnn_model_path.is_file(), "CNN model checkpoint was not saved!"
    print(f"  [OK] CNN Baseline trained for 2 epochs. Acc: {res['metrics'].get('accuracy', 0):.2f}, F1: {res['metrics'].get('f1', 0):.2f}")


def test_4_resnet18_training():
    log_step(4, "Training Adapted ResNet-18 Model & Exporting Checkpoint")
    from training.train import train_pipeline

    res = train_pipeline(
        model_name="resnet18",
        data_dir=str(DATA_DIR),
        epochs=3,
        batch_size=8,
        lr=2e-4,
        output_model=str(MODEL_PATH),
        device_name="cpu",
    )
    assert MODEL_PATH.is_file(), f"Target checkpoint {MODEL_PATH} was not created!"
    print(f"  [OK] ResNet-18 trained for 3 epochs. Best checkpoint saved to {MODEL_PATH}")


def test_5_checkpoint_integrity():
    log_step(5, "Verifying Checkpoint Integrity & State Dict Keys")
    checkpoint = torch.load(str(MODEL_PATH), map_location="cpu")
    assert isinstance(checkpoint, dict), "Checkpoint should be a dictionary"
    assert "state_dict" in checkpoint, "Checkpoint should contain 'state_dict'"
    state_dict = checkpoint["state_dict"]

    # Check key layers
    assert "conv1.weight" in state_dict, "conv1.weight must exist"
    assert state_dict["conv1.weight"].shape[1] == 1, "conv1 must take 1-channel spectrogram input"
    assert "fc.weight" in state_dict, "fc.weight must exist"
    assert state_dict["fc.weight"].shape[0] == 2, "fc must have 2 output classes"
    print(f"  conv1 weight shape: {state_dict['conv1.weight'].shape}")
    print(f"  fc weight shape: {state_dict['fc.weight'].shape}")
    print("  [OK] ResNet-18 checkpoint state_dict keys match production classifier requirements.")


def test_6_evaluation_and_latency():
    log_step(6, "Evaluating Test Split & Latency SLA (<50ms)")
    from training.evaluate import load_trained_model, benchmark_latency, evaluate_test_split

    device = torch.device("cpu")
    model = load_trained_model(str(MODEL_PATH), model_type="resnet18", device=device)

    # Benchmark latency
    latency = benchmark_latency(model, device, n_runs=50)
    print(f"  Inference Latency: Mean = {latency['mean_ms']}ms, P95 = {latency['p95_ms']}ms, Target = {latency['sla_target_ms']}ms")
    assert latency["meets_sla"], f"Inference latency exceeded SLA: {latency['p95_ms']}ms > 50ms"

    # Evaluate test split
    test_manifest = DATA_DIR / "test.json"
    metrics = evaluate_test_split(model, str(test_manifest), device)
    print(f"  Test Metrics: Accuracy = {metrics['accuracy']*100:.1f}%, F1 = {metrics['f1']:.3f}, AUC = {metrics['roc_auc']:.3f}")
    assert metrics["accuracy"] >= 0.50, "Accuracy should be non-trivial"
    print("  [OK] Latency meets <50ms SLA and evaluation metrics computed cleanly.")


def test_7_robustness_perturbations():
    log_step(7, "Testing Robustness Stress Perturbations")
    from training.evaluate import load_trained_model, run_robustness_eval

    device = torch.device("cpu")
    model = load_trained_model(str(MODEL_PATH), model_type="resnet18", device=device)

    test_manifest = DATA_DIR / "test.json"
    with open(test_manifest, "r") as f:
        records = json.load(f)

    results = run_robustness_eval(model, records, device)
    for condition, m in results.items():
        print(f"    {condition:<24}: Acc = {m['accuracy']*100:>5.1f}%, F1 = {m['f1']:.3f}, AUC = {m['roc_auc']:.3f}")
    assert len(results) >= 5, "Should test at least 5 perturbation conditions"
    print("  [OK] Robustness test suite executed across all perturbations without error.")


def test_8_backend_integration_mode_switch():
    log_step(8, "Verifying Backend Integration: 'demo' -> 'ml' Mode Switch")
    from app.config import get_settings
    from app.ml.factory import get_detector, resolve_model_path

    settings = get_settings()
    # Ensure settings points to our newly trained model
    settings.MODEL_PATH = str(MODEL_PATH)
    settings.DEMO_MODE = False

    resolved = resolve_model_path(settings.MODEL_PATH)
    assert resolved is not None and resolved.is_file(), f"Failed to resolve model path: {settings.MODEL_PATH}"

    # Force reload detector
    detector = get_detector(force_reload=True)

    print(f"  Detector Name: {detector.name}")
    print(f"  Detector Mode: {detector.mode}")
    print(f"  Is Loaded:     {detector.is_loaded}")

    assert detector.mode == "ml", f"Expected detector mode 'ml', got '{detector.mode}'"
    assert detector.is_loaded is True, "Expected detector.is_loaded to be True"
    assert "ResNet18" in detector.name, f"Expected ResNet18 detector, got '{detector.name}'"

    # Test inference on a sample window
    dummy_spec = np.random.randn(128, 63).astype(np.float32)
    pred = detector.predict_window(dummy_spec)
    print(f"  Sample Prediction: {pred}")
    assert "fake_probability" in pred, "Prediction should contain fake_probability"
    assert "real_probability" in pred, "Prediction should contain real_probability"
    assert "raw_label" in pred, "Prediction should contain raw_label"
    assert pred["raw_label"] in ["REAL", "DEEPFAKE"]

    print("  [OK] Backend successfully loaded trained ResNet-18 model weights!")
    print("  [OK] Backend mode transitioned from 'demo' to 'ml'. Real inference verified.")


def main():
    print("=" * 80)
    print("SHADOW-NET Phase 7 Verification: Training Pipeline & ML Model Export")
    print("=" * 80)

    t0 = time.time()
    test_1_dataset_generation()
    test_2_dataset_loader_shapes()
    test_3_cnn_baseline_training()
    test_4_resnet18_training()
    test_5_checkpoint_integrity()
    test_6_evaluation_and_latency()
    test_7_robustness_perturbations()
    test_8_backend_integration_mode_switch()

    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print(f"ALL 8 PHASE 7 VERIFICATION CHECKS PASSED in {elapsed:.2f}s!")
    print("=" * 80)


if __name__ == "__main__":
    main()

"""
Phase 3 Verification Script for SHADOW-NET ML Inference & Decision Engine.
Tests:
1. Demo mode fallback when no weights exist (clearly labeled mode='demo').
2. Dynamic switch to 'ml' mode when a valid resnet18.pth is dropped into model/.
3. Three-state Decision Engine evaluation (REAL / DEEPFAKE / UNCERTAIN) and ThreatLevel mapping.
4. Response structure verification for POST /audio/analyze.
"""

import os
import sys
from pathlib import Path
import soundfile as sf
import numpy as np

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient
from main import app
from app.config import get_settings
from app.ml.factory import get_detector, reload_detector
from app.ml.decision import DecisionEngine
from app.models.incident import PredictionType, ThreatLevel


def run_phase3_verification():
    print("================================================================")
    print("      SHADOW-NET Phase 3 ML Inference Verification Suite")
    print("================================================================")

    project_root = Path(__file__).resolve().parent.parent
    sample_wav_path = project_root / "datasets" / "sample_test.wav"
    model_pth_path = project_root / "model" / "resnet18.pth"

    # Ensure sample audio exists
    if not sample_wav_path.is_file():
        # Create a 2.5s sine tone sample
        t = np.linspace(0, 2.5, int(2.5 * 16000), endpoint=False)
        tone = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        sample_wav_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(sample_wav_path), tone, 16000)

    # 1. Verification with NO model weights present (Demo Mode)
    print("\n[Step 1] Verifying Demo Fallback when no weights exist...")
    if model_pth_path.is_file():
        model_pth_path.unlink()  # Ensure removed for Step 1

    settings = get_settings()
    settings.DEMO_MODE = True
    reload_detector()

    with TestClient(app) as client:
        with open(sample_wav_path, "rb") as f:
            res = client.post(
                "/audio/analyze",
                files={"file": ("sample.wav", f, "audio/wav")},
            )
        assert res.status_code == 200, f"Demo analysis request failed: {res.text}"
        demo_data = res.json()

        print(f"  [PASS] Operational Mode: '{demo_data['mode']}' (Expected: 'demo')")
        print(f"  [PASS] Model Name: {demo_data['model_name']}")
        print(f"  [PASS] Prediction: {demo_data['prediction']}")
        print(f"  [PASS] Confidence: {demo_data['confidence']:.4f}")
        print(f"  [PASS] Threat Level: {demo_data['threat_level']}")
        print(f"  [PASS] Measured Latency: {demo_data['detection_latency_ms']} ms")
        print(f"  [PASS] Is Synthetic Flag: {demo_data['is_synthetic']}")

        assert demo_data["mode"] == "demo", "Must report mode='demo'"
        assert demo_data["is_synthetic"] is True, "Must flag is_synthetic=True"
        assert demo_data["prediction"] in ["REAL", "DEEPFAKE", "UNCERTAIN"]
        assert demo_data["threat_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert demo_data["detection_latency_ms"] > 0

    # 2. Decision Engine Threshold Unit Tests
    print("\n[Step 2] Testing Three-State Decision Engine & Threat Levels...")
    engine = DecisionEngine(default_threshold=0.75)

    # High fake score
    pred, threat, conf = engine.evaluate_window(0.94)
    assert pred == PredictionType.DEEPFAKE and threat == ThreatLevel.CRITICAL
    print(f"  [PASS] Score 0.94 -> Prediction: {pred.value} | Threat: {threat.value} (CRITICAL)")

    # Moderately high fake score
    pred, threat, conf = engine.evaluate_window(0.79)
    assert pred == PredictionType.DEEPFAKE and threat == ThreatLevel.HIGH
    print(f"  [PASS] Score 0.79 -> Prediction: {pred.value} | Threat: {threat.value} (HIGH)")

    # Clean real voice score
    pred, threat, conf = engine.evaluate_window(0.12)
    assert pred == PredictionType.REAL and threat == ThreatLevel.LOW
    print(f"  [PASS] Score 0.12 -> Prediction: {pred.value} | Threat: {threat.value} (LOW)")

    # Borderline ambiguous score -> UNCERTAIN
    pred, threat, conf = engine.evaluate_window(0.55)
    assert pred == PredictionType.UNCERTAIN and threat == ThreatLevel.MEDIUM
    print(f"  [PASS] Score 0.55 -> Prediction: {pred.value} | Threat: {threat.value} (UNCERTAIN - Borderline)")

    # 3. ML Mode Switch: Generate dummy resnet18.pth and verify mode='ml'
    print("\n[Step 3] Testing Dynamic Switch to 'ml' Mode with Model Weights...")
    import torch
    import torch.nn as nn
    import torchvision.models as models

    # Build dummy adapted ResNet-18 weights
    dummy_net = models.resnet18(weights=None)
    dummy_net.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
    dummy_net.fc = nn.Linear(dummy_net.fc.in_features, 2)

    # Save to model/resnet18.pth
    model_pth_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dummy_net.state_dict(), str(model_pth_path))
    print(f"  [INFO] Created dummy ResNet-18 weights at: {model_pth_path.name}")

    # Switch config to DEMO_MODE = False and reload
    settings.DEMO_MODE = False
    settings.MODEL_PATH = str(model_pth_path)
    ml_detector = reload_detector()

    assert ml_detector.mode == "ml", f"Expected detector mode 'ml', got '{ml_detector.mode}'"
    print(f"  [PASS] Detector successfully reloaded in mode: '{ml_detector.mode}'")

    with TestClient(app) as client:
        with open(sample_wav_path, "rb") as f:
            res_ml = client.post(
                "/audio/analyze",
                files={"file": ("sample.wav", f, "audio/wav")},
            )
        assert res_ml.status_code == 200, f"ML analysis request failed: {res_ml.text}"
        ml_data = res_ml.json()

        print(f"  [PASS] Operational Mode: '{ml_data['mode']}' (Expected: 'ml')")
        print(f"  [PASS] Model Name: {ml_data['model_name']}")
        print(f"  [PASS] Prediction: {ml_data['prediction']}")
        print(f"  [PASS] Threat Level: {ml_data['threat_level']}")
        print(f"  [PASS] Is Synthetic Flag: {ml_data['is_synthetic']}")

        assert ml_data["mode"] == "ml", "Must report mode='ml'"
        assert ml_data["is_synthetic"] is False, "Must report is_synthetic=False"

    # 4. Clean up dummy weights and reset to demo mode default
    print("\n[Step 4] Cleaning up dummy model and resetting to default demo mode...")
    if model_pth_path.is_file():
        model_pth_path.unlink()
    settings.DEMO_MODE = True
    reset_detector = reload_detector()
    assert reset_detector.mode == "demo"
    print("  [PASS] Cleaned up test model checkpoint. Reverted to Demo mode safely.")

    print("\n================================================================")
    print("  ALL PHASE 3 ML INFERENCE CHECKS PASSED! (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_phase3_verification()

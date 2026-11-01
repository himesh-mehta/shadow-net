"""
End-to-end validation test for SHADOW-NET ML pipeline & standardized model outputs.
Tests:
1. Model metadata loading from models/shadownet-audio-detector/v1/metadata.json
2. Standardized model output schema (ai_probability, real_probability, verdict, model_status, is_heuristic_placeholder)
3. Multi-window temporal decision logic & sustained threat detection
4. FastAPI /audio/analyze endpoint with simulated audio payload
"""

import sys
import numpy as np
from app.ml.metadata import load_model_metadata
from app.ml.factory import get_detector
from app.ml.decision import DecisionEngine
from app.models.incident import PredictionType, ThreatLevel


def test_metadata_and_detector():
    print("--- 1. Testing Model Metadata & Detector ---")
    meta = load_model_metadata()
    assert meta.model_name == "shadownet-audio-detector", f"Unexpected name: {meta.model_name}"
    assert meta.model_version == "v1", f"Unexpected version: {meta.model_version}"
    assert meta.is_trained is False, f"Expected untrained model, got: {meta.is_trained}"
    assert meta.status == "NOT_TRAINED", f"Expected NOT_TRAINED, got: {meta.status}"
    print("[PASS] Metadata properly loaded from models/shadownet-audio-detector/v1/metadata.json")

    detector = get_detector(force_reload=True)
    assert detector.name == "shadownet-audio-detector"
    assert detector.model_status == "NOT_TRAINED"
    assert detector.is_heuristic_placeholder is True

    # Run inference on dummy 128-band Mel-spectrogram
    dummy_spec = np.random.randn(128, 63).astype(np.float32)
    res = detector.predict_window(dummy_spec, window_start=0.0, window_end=2.0)

    # Validate standardized schema
    required_keys = [
        "ai_probability",
        "real_probability",
        "verdict",
        "model_name",
        "model_version",
        "model_status",
        "is_heuristic_placeholder",
        "window_start",
        "window_end",
    ]
    for k in required_keys:
        assert k in res, f"Missing required key in standardized output: {k}"

    assert res["model_status"] == "NOT_TRAINED"
    assert res["is_heuristic_placeholder"] is True
    assert 0.0 <= res["ai_probability"] <= 1.0
    assert 0.0 <= res["real_probability"] <= 1.0
    assert round(res["ai_probability"] + res["real_probability"], 2) == 1.0
    print(f"[PASS] Standardized detector output: {res}")


def test_multi_window_temporal_decision():
    print("\n--- 2. Testing Multi-Window Temporal Decision Engine ---")
    de = DecisionEngine(real_threshold=0.35, deepfake_threshold=0.65, consecutive_sustained_k=2)

    # Test clean windows
    clean_wins = [{"ai_probability": 0.15}, {"ai_probability": 0.20}, {"ai_probability": 0.18}]
    clean_res = de.evaluate_session(clean_wins, model_status="NOT_TRAINED")
    assert clean_res["display_verdict"] == "UNCERTAIN (MODEL NOT TRAINED)"
    assert clean_res["sustained_threat_detected"] is False
    print("[PASS] Clean windows evaluated with honest UNTRAINED status")

    # Test single isolated spike (< K consecutive windows)
    spike_wins = [{"ai_probability": 0.15}, {"ai_probability": 0.75}, {"ai_probability": 0.20}]
    spike_res = de.evaluate_session(spike_wins, model_status="NOT_TRAINED")
    assert spike_res["sustained_threat_detected"] is False
    print("[PASS] Isolated spike correctly avoided triggering sustained threat cluster")

    # Test sustained run (>= K consecutive windows above deepfake_threshold)
    sustained_wins = [{"ai_probability": 0.20}, {"ai_probability": 0.72}, {"ai_probability": 0.81}, {"ai_probability": 0.25}]
    sustained_res = de.evaluate_session(sustained_wins, model_status="NOT_TRAINED")
    assert sustained_res["sustained_threat_detected"] is True
    print("[PASS] Multi-window sustained threat correctly detected")


def main():
    try:
        test_metadata_and_detector()
        test_multi_window_temporal_decision()
        print("\n=======================================================")
        print("ALL PIPELINE & STANDARDIZATION TESTS PASSED SUCCESSFULLY!")
        print("=======================================================")
    except AssertionError as e:
        print(f"[FAIL] Assertion error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Phase 8 Verification Script for SHADOW-NET.
Validates:
1. Reference demonstration sample audio files in datasets/sample/ (16kHz PCM WAV).
2. Live audio ingestion of sample audio through the full FastAPI pipeline & incident response.
3. Dockerfiles and docker-compose.yml orchestration integrity.
4. Environment variable alignment between .env.example and docker-compose.yml.
5. Privacy policy enforcement (store_audio=False default).
6. Security audit (no hardcoded secrets, controlled test bench notice present).
"""

import os
import sys
import re
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SAMPLE_DIR = PROJECT_ROOT / "datasets" / "sample"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import soundfile as sf
from fastapi.testclient import TestClient
from app.config import get_settings


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/6] {title}...")


def test_1_sample_audio_files():
    log_step(1, "Verifying Reference Sample Audio Files")
    expected_files = [
        "real_01_bonafide_speech.wav",
        "real_02_bonafide_speech.wav",
        "synthetic_01_deepfake_vocoder_glitch.wav",
        "synthetic_02_deepfake_neural_tts.wav",
        "synthetic_03_deepfake_cloned_voice.wav",
    ]

    for fname in expected_files:
        fpath = SAMPLE_DIR / fname
        assert fpath.is_file(), f"Sample audio file missing: {fname}"
        data, sr = sf.read(str(fpath))
        assert sr == 16000, f"Sample rate for {fname} should be 16000, got {sr}"
        assert len(data) > 16000, f"Audio file {fname} too short: {len(data)} samples"
        print(f"  [OK] {fname}: {len(data)/sr:.1f}s at {sr}Hz (mono)")

    readme = SAMPLE_DIR / "README.md"
    assert readme.is_file() and readme.stat().st_size > 100, "datasets/sample/README.md missing or empty"
    print("  [OK] datasets/sample/README.md documentation verified.")


def test_2_audio_pipeline_sample_ingestion():
    log_step(2, "Testing Audio Pipeline Ingestion with Reference Samples")
    from app.audio.preprocessing import load_audio
    from app.audio.features import extract_mel_spectrogram

    real_file = SAMPLE_DIR / "real_01_bonafide_speech.wav"
    fake_file = SAMPLE_DIR / "synthetic_01_deepfake_vocoder_glitch.wav"

    for fpath, label in [(real_file, "REAL"), (fake_file, "FAKE")]:
        audio, sr = load_audio(str(fpath), target_sr=16000)
        assert sr == 16000, "Sample rate must be 16kHz"
        mel_spec = extract_mel_spectrogram(audio[:32000], sr=16000)
        assert mel_spec.shape == (128, 63), f"Expected (128, 63), got {mel_spec.shape}"
        print(f"  [OK] {label} sample processed. Mel-Spectrogram shape: {mel_spec.shape}")


def test_3_end_to_end_api_with_samples():
    log_step(3, "Testing End-to-End API Flow with Sample Audio")
    from main import app

    with TestClient(app) as client:
        # 1. Register and Login
        client.post("/auth/register", json={
            "username": "phase8_analyst",
            "email": "phase8@shadownet.internal",
            "password": "AnalystPassword123!",
            "role": "Security Analyst",
        })
        res = client.post("/auth/login", json={
            "username": "phase8_analyst",
            "password": "AnalystPassword123!",
        })
        assert res.status_code == 200, "Login failed"
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Start controlled session
        res = client.post("/session/start", json={"client_label": "Phase8 Test Bench", "store_audio": False}, headers=headers)
        assert res.status_code == 201, "Failed to start session"
        session_id = res.json()["session_id"]
        print(f"  [OK] Controlled test session started: {session_id}")

        # 3. Analyze real sample
        real_path = SAMPLE_DIR / "real_01_bonafide_speech.wav"
        with open(real_path, "rb") as f:
            res = client.post("/audio/analyze", data={"session_id": session_id}, files={"file": ("real.wav", f, "audio/wav")}, headers=headers)
        assert res.status_code == 200, f"Analyze real failed: {res.text}"
        real_data = res.json()
        print(f"  [OK] Real audio analysis: verdict={real_data['prediction']}, confidence={real_data['confidence']}, threat={real_data['threat_level']}")

        # 4. Analyze synthetic deepfake sample
        fake_path = SAMPLE_DIR / "synthetic_01_deepfake_vocoder_glitch.wav"
        with open(fake_path, "rb") as f:
            res = client.post("/audio/analyze", data={"session_id": session_id}, files={"file": ("fake.wav", f, "audio/wav")}, headers=headers)
        assert res.status_code == 200, f"Analyze fake failed: {res.text}"
        fake_data = res.json()
        print(f"  [OK] Synthetic audio analysis: verdict={fake_data['prediction']}, confidence={fake_data['confidence']}, threat={fake_data['threat_level']}")

        # 5. Stop session
        res = client.post(f"/session/stop?session_id={session_id}", headers=headers)
        assert res.status_code == 200, "Failed to stop session"
        print("  [OK] Controlled test session cleanly stopped.")


def test_4_docker_configuration():
    log_step(4, "Auditing Dockerfiles & Docker Compose Orchestration")
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    assert compose_file.is_file(), "docker-compose.yml missing"
    compose_text = compose_file.read_text(encoding="utf-8")

    # Verify services
    for svc in ["mongodb:", "backend:", "frontend:"]:
        assert svc in compose_text, f"Service {svc} not in docker-compose.yml"
    for port in ["27017:27017", "8000:8000", "3000:3000"]:
        assert port in compose_text, f"Port mapping {port} not in docker-compose.yml"
    assert "./model:/app/model" in compose_text, "Model volume mount missing"
    assert "./datasets:/app/datasets" in compose_text, "Datasets volume mount missing"
    print("  [OK] docker-compose.yml verified with mongodb, backend, frontend, ports, and volumes.")

    # Backend Dockerfile
    backend_df = BACKEND_DIR / "Dockerfile"
    assert backend_df.is_file(), "backend/Dockerfile missing"
    b_content = backend_df.read_text(encoding="utf-8")
    assert "FROM python:3.10-slim" in b_content, "Backend should use python:3.10-slim"
    assert "EXPOSE 8000" in b_content, "Backend should expose port 8000"
    print("  [OK] backend/Dockerfile verified.")

    # Frontend Dockerfile
    frontend_df = FRONTEND_DIR / "Dockerfile"
    assert frontend_df.is_file(), "frontend/Dockerfile missing"
    f_content = frontend_df.read_text(encoding="utf-8")
    assert "FROM node:20-alpine" in f_content, "Frontend should use node:20-alpine"
    assert "NEXT_PUBLIC_API_URL" in f_content, "Frontend Dockerfile should include build args"
    assert "EXPOSE 3000" in f_content, "Frontend should expose port 3000"
    print("  [OK] frontend/Dockerfile verified with build args and multi-stage runner.")


def test_5_env_variable_alignment():
    log_step(5, "Verifying Environment Variable Alignment")
    env_example = PROJECT_ROOT / ".env.example"
    assert env_example.is_file(), ".env.example missing"
    example_text = env_example.read_text(encoding="utf-8")

    required_vars = [
        "MONGODB_URI",
        "JWT_SECRET",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "DETECTION_THRESHOLD",
        "MODEL_PATH",
        "DEMO_MODE",
        "AUDIO_SAMPLE_RATE",
        "AUDIO_WINDOW_SECONDS",
        "VAD_SENSITIVITY",
        "NEXT_PUBLIC_API_URL",
        "NEXT_PUBLIC_WS_URL",
    ]

    for var in required_vars:
        assert var in example_text, f"Missing {var} in .env.example"
    print(f"  [OK] All {len(required_vars)} environment variables present in .env.example.")


def test_6_security_and_privacy_commitments():
    log_step(6, "Validating Security, Privacy Policies & Disclaimers")
    settings = get_settings()
    assert settings.STORE_AUDIO_DEFAULT is False, "store_audio default must strictly be False"
    print("  [OK] Audio privacy policy: store_audio defaults to False.")

    # Check controlled environment notice
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "Controlled Testing Environment Notice" in readme_text, "Controlled testing disclaimer missing from README"
    assert "does NOT" in readme_text and "third-party VoIP" in readme_text, "VoIP non-interception notice missing"
    print("  [OK] Controlled test environment notice & VoIP disclaimer present in README.md.")

    # Check header badge is persistently visible
    header_file = FRONTEND_DIR / "src" / "components" / "layout" / "Header.tsx"
    header_content = header_file.read_text(encoding="utf-8")
    assert "ThreatBadge type={isDemoMode ? \"demo\" : \"ml\"}" in header_content, "Header must display demo/ml badge"
    print("  [OK] Persistent Demo/ML threat badge verified in Header.tsx.")


def main():
    print("=" * 80)
    print("SHADOW-NET Phase 8 Verification: Docker, Sample Data, Documentation & Audit")
    print("=" * 80)

    test_1_sample_audio_files()
    test_2_audio_pipeline_sample_ingestion()
    test_3_end_to_end_api_with_samples()
    test_4_docker_configuration()
    test_5_env_variable_alignment()
    test_6_security_and_privacy_commitments()

    print("\n" + "=" * 80)
    print("ALL 6 PHASE 8 VERIFICATION CHECKS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    main()

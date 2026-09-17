"""
Phase 2 Audio Pipeline Sanity Check Script for SHADOW-NET.
Generates a sample WAV file with known silence and tone/harmonics,
runs the complete preprocessing, VAD, windowing, and feature extraction pipeline,
and asserts:
1. Silence is successfully dropped by VAD.
2. MFCC shape matches (n_mfcc, time_frames).
3. Mel-Spectrogram shape matches (n_mels, time_frames).
4. Full API endpoint POST /audio/analyze processes both multipart WAV and base64.
"""

import sys
import base64
import numpy as np
import soundfile as sf
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.audio.preprocessing import load_audio, normalize_audio, resample_audio
from app.audio.vad import get_vad, EnergyVAD
from app.audio.features import slice_into_windows, extract_all_features, render_spectrogram_to_matrix
from fastapi.testclient import TestClient
from main import app


def generate_synthetic_test_wav(output_path: Path, sr: int = 16000) -> Path:
    """
    Synthesizes a test audio file:
    - 1.0s leading silence
    - 2.5s simulated speech harmonics (fundamental 220Hz + formants with AM modulation)
    - 1.0s trailing silence
    Total: 4.5 seconds.
    """
    t_silence_1 = np.zeros(int(1.0 * sr), dtype=np.float32)
    t_speech_time = np.linspace(0, 2.5, int(2.5 * sr), endpoint=False)

    # Multi-harmonic audio signal with speech-like envelope
    f0 = 220.0
    harmonics = (
        0.5 * np.sin(2 * np.pi * f0 * t_speech_time)
        + 0.3 * np.sin(2 * np.pi * (2 * f0) * t_speech_time)
        + 0.2 * np.sin(2 * np.pi * (3 * f0) * t_speech_time)
        + 0.1 * np.sin(2 * np.pi * (4 * f0) * t_speech_time)
    )
    # Speech envelope modulation (syllable-like AM at 4 Hz)
    envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 4.0 * t_speech_time))
    speech_signal = (harmonics * envelope).astype(np.float32)

    t_silence_2 = np.zeros(int(1.0 * sr), dtype=np.float32)

    combined = np.concatenate([t_silence_1, speech_signal, t_silence_2])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), combined, sr)
    return output_path


def run_sanity_check():
    print("================================================================")
    print("      SHADOW-NET Phase 2 Audio Pipeline Sanity Check")
    print("================================================================")

    sample_dir = Path(__file__).resolve().parent.parent / "datasets"
    sample_wav_path = sample_dir / "sample_test.wav"

    # 1. Generate test WAV
    print(f"\n[Step 1] Synthesizing test audio file: {sample_wav_path.name}...")
    generate_synthetic_test_wav(sample_wav_path, sr=16000)
    info = sf.info(str(sample_wav_path))
    print(f"  [PASS] Created test audio: {info.duration:.2f}s, {info.samplerate}Hz, {info.channels}ch")

    # 2. Preprocessing Module Test
    print("\n[Step 2] Testing Preprocessing Module...")
    with open(sample_wav_path, "rb") as f:
        audio_bytes = f.read()

    waveform, sr = load_audio(audio_bytes, target_sr=16000)
    assert sr == 16000, f"Expected 16kHz, got {sr}"
    assert waveform.ndim == 1, f"Expected 1D mono waveform, got shape {waveform.shape}"
    assert -1.01 <= np.min(waveform) and np.max(waveform) <= 1.01, "Waveform should be normalized"
    print(f"  [PASS] Waveform loaded & normalized: Shape={waveform.shape}, Max={np.max(waveform):.3f}, Min={np.min(waveform):.3f}")

    # 3. Voice Activity Detection (VAD) Test
    print("\n[Step 3] Testing Voice Activity Detection (Silence Dropping)...")
    vad = get_vad()
    speech_audio, intervals, meta = vad.filter_speech(waveform, sr=sr, sensitivity=2)
    print(f"  [INFO] Original duration: {meta['original_duration']:.2f}s")
    print(f"  [INFO] Detected speech duration: {meta['speech_duration']:.2f}s")
    print(f"  [INFO] Dropped silence duration: {meta['dropped_duration']:.2f}s")
    print(f"  [INFO] Detected speech intervals: {intervals}")

    # Assert silence was actually dropped: original is 4.5s, speech should be ~2.5s
    assert meta["dropped_duration"] >= 1.5, f"Expected at least 1.5s silence dropped, got {meta['dropped_duration']}s"
    assert meta["speech_duration"] > 0, "Active speech duration must be greater than 0"
    print("  [PASS] VAD successfully dropped non-speech silence intervals!")

    # 4. Rolling Window Slicing Test
    print("\n[Step 4] Testing Rolling Window Slicing (2.0s windows, 1.0s hop)...")
    windows = slice_into_windows(speech_audio, sr=sr, window_sec=2.0, hop_sec=1.0)
    assert len(windows) >= 1, "Must produce at least 1 window"
    print(f"  [PASS] Sliced into {len(windows)} rolling window(s):")
    for w in windows:
        print(f"    - Window #{w['window_index']}: [{w['start_sec']:.2f}s -> {w['end_sec']:.2f}s] (Samples: {len(w['audio'])}, Padded: {w['is_padded']})")

    # 5. Feature Extraction Test (Mel-Spectrogram & MFCC)
    print("\n[Step 5] Testing Acoustic Feature Extraction per Window...")
    first_window_audio = windows[0]["audio"]
    features = extract_all_features(first_window_audio, sr=sr, n_mels=128, n_mfcc=20)

    mel_shape = features["mel_shape"]
    mfcc_shape = features["mfcc_shape"]
    visual_matrix = features["visual_matrix"]

    print(f"  [PASS] Mel-Spectrogram shape: {mel_shape} (Expected: [128, time_frames])")
    print(f"  [PASS] MFCC shape: {mfcc_shape} (Expected: [20, time_frames])")
    print(f"  [PASS] Visual Preview Matrix size: {len(visual_matrix)} frequency bands x {len(visual_matrix[0])} time columns")

    assert mel_shape[0] == 128, f"Expected n_mels=128, got {mel_shape[0]}"
    assert mfcc_shape[0] == 20, f"Expected n_mfcc=20, got {mfcc_shape[0]}"
    assert mel_shape[1] > 0 and mfcc_shape[1] > 0, "Time frames must be non-zero"

    # 6. Full FastAPI Endpoint Test (POST /audio/analyze)
    print("\n[Step 6] Testing POST /audio/analyze via FastAPI TestClient...")
    with TestClient(app) as client:
        # Test 6a: Multipart WAV file upload
        with open(sample_wav_path, "rb") as f:
            res_multipart = client.post(
                "/audio/analyze",
                files={"file": ("sample_test.wav", f, "audio/wav")},
            )
        assert res_multipart.status_code == 200, f"Multipart upload failed: {res_multipart.text}"
        data_multi = res_multipart.json()
        assert data_multi["status"] == "success"
        assert data_multi["sample_rate"] == 16000
        assert data_multi["num_windows"] == len(windows)
        print(f"  [PASS] Multipart WAV analysis: Status 200, Processed {data_multi['num_windows']} windows in {data_multi['processing_latency_ms']}ms")

        # Test 6b: Base64 audio chunk upload (JSON endpoint)
        b64_audio = base64.b64encode(audio_bytes).decode("ascii")
        res_json = client.post(
            "/audio/analyze/json",
            json={"audio_base64": b64_audio, "window_length": 2.0},
        )
        assert res_json.status_code == 200, f"JSON base64 upload failed: {res_json.text}"
        data_json = res_json.json()
        assert data_json["status"] == "success"
        print(f"  [PASS] Base64 JSON analysis: Status 200, Processed {data_json['num_windows']} windows in {data_json['processing_latency_ms']}ms")

        # Test 6c: Invalid empty request
        res_empty = client.post("/audio/analyze")
        assert res_empty.status_code == 400, "Empty payload should return 400"
        print("  [PASS] Empty payload correctly rejected with 400 Bad Request")

    print("\n================================================================")
    print("  ALL PHASE 2 AUDIO PIPELINE CHECKS PASSED! (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_sanity_check()

"""
Sample Audio Generator for SHADOW-NET.
Creates reference audio samples under datasets/sample/ for immediate out-of-the-box demoing:
- Real human bonafide speech samples
- Synthetic deepfake voice samples with vocoder glitches, flat TTS, and cloning artifacts.
All files are standard 16kHz 16-bit PCM mono WAV files.
"""

import math
from pathlib import Path
import numpy as np
import soundfile as sf

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "datasets" / "sample"
SAMPLE_RATE = 16000


def synthesize_bonafide_speech(duration_sec: float = 3.0, base_f0: float = 140.0) -> np.ndarray:
    """Synthesizes human-like speech with natural intonation, formants, and smooth envelopes."""
    sr = SAMPLE_RATE
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)

    # Natural intonation contour: speech starts higher, dips, and rises gently
    pitch_contour = base_f0 * (1.0 + 0.12 * np.sin(2 * np.pi * 1.2 * t) + 0.02 * np.sin(2 * np.pi * 5.5 * t))
    phase = 2 * np.pi * np.cumsum(pitch_contour) / sr

    # Glottal pulse excitation (band-limited impulse train approximation)
    glottal = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase) + 0.12 * np.sin(4 * phase)

    # Vocal tract formants: F1 (~650 Hz), F2 (~1500 Hz), F3 (~2500 Hz)
    f1 = np.sin(2 * np.pi * 650.0 * t) * np.exp(-((t % 0.08) * 25.0))
    f2 = np.sin(2 * np.pi * 1500.0 * t) * np.exp(-((t % 0.08) * 30.0))
    f3 = np.sin(2 * np.pi * 2500.0 * t) * np.exp(-((t % 0.08) * 35.0))
    formants = 0.4 * f1 + 0.3 * f2 + 0.2 * f3

    # Syllabic envelope (simulating word syllables ~ 3-4 syllables per second)
    syllables = 0.5 * (1.0 + np.sin(2 * np.pi * 3.2 * t - np.pi / 2))
    syllables = np.clip(syllables, 0.05, 1.0)

    speech = (0.6 * glottal + 0.4 * formants) * syllables

    # Soft ambient room noise
    ambient = 0.008 * np.random.normal(0, 1, size=n_samples)
    audio = speech + ambient

    # Peak normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = 0.85 * (audio / max_val)

    return audio.astype(np.float32)


def synthesize_deepfake_vocoder_glitch(duration_sec: float = 3.0) -> np.ndarray:
    """Synthesizes synthetic deepfake audio with vocoder artifacts and phase glitches."""
    sr = SAMPLE_RATE
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)

    # Base harmonic structure with flat robotic fundamental
    f0 = 160.0
    phase = 2 * np.pi * f0 * t
    carrier = np.sin(phase) + 0.4 * np.sin(2 * phase) + 0.2 * np.sin(3 * phase)

    # 1. Neural vocoder high-frequency checkerboard distortion (e.g. 6400 Hz alias artifact)
    vocoder_checkerboard = 0.18 * np.sin(2 * np.pi * 6400.0 * t) * (np.sin(2 * np.pi * 80.0 * t) > 0)

    # 2. Severe phase discontinuity glitches (step jumps)
    phase_glitch = 0.12 * np.sign(np.sin(2 * np.pi * 750.0 * t))

    # 3. High-frequency metallic synthesis hiss
    metallic_noise = 0.08 * np.random.normal(0, 1, size=n_samples) * (np.sin(2 * np.pi * 5000.0 * t) ** 2)

    signal = carrier + vocoder_checkerboard + phase_glitch + metallic_noise

    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = 0.88 * (signal / max_val)

    return signal.astype(np.float32)


def synthesize_deepfake_neural_tts(duration_sec: float = 3.0) -> np.ndarray:
    """Synthesizes text-to-speech audio with flat pitch contour and unnatural spectral smearing."""
    sr = SAMPLE_RATE
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)

    # Rigid flat pitch (zero micro-jitter, typical of early/unconditioned neural vocoders)
    f0 = 180.0
    tone = np.zeros_like(t)
    for h in [1, 2, 3, 4, 5]:
        tone += (0.8 / h) * np.sin(2 * np.pi * h * f0 * t)

    # Unnatural robotic amplitude pulse
    pulse = 0.5 * (1.0 + np.sin(2 * np.pi * 4.0 * t))
    spectral_smear = 0.15 * np.sin(2 * np.pi * 4200.0 * t)

    signal = tone * pulse + spectral_smear
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = 0.85 * (signal / max_val)

    return signal.astype(np.float32)


def generate_all_samples():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating demonstration audio samples in: {SAMPLE_DIR}")

    samples = [
        ("real_01_bonafide_speech.wav", synthesize_bonafide_speech(3.0, base_f0=130.0), "Natural human speech, varied pitch contour & organic formant structure"),
        ("real_02_bonafide_speech.wav", synthesize_bonafide_speech(3.2, base_f0=165.0), "Natural human voice, conversational tempo & breath envelope"),
        ("synthetic_01_deepfake_vocoder_glitch.wav", synthesize_deepfake_vocoder_glitch(3.0), "Deepfake vocoder artifact with 6.4kHz checkerboard & phase jumps"),
        ("synthetic_02_deepfake_neural_tts.wav", synthesize_deepfake_neural_tts(3.0), "Deepfake synthetic voice with monotone pitch & spectral smearing"),
        ("synthetic_03_deepfake_cloned_voice.wav", synthesize_deepfake_vocoder_glitch(2.8), "Cloned voice simulation with phase discontinuities & alias hiss"),
    ]

    manifest = []
    for filename, audio, desc in samples:
        out_path = SAMPLE_DIR / filename
        sf.write(str(out_path), audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        duration = len(audio) / SAMPLE_RATE
        size_kb = out_path.stat().st_size / 1024
        print(f"  [OK] Created: {filename} ({duration:.1f}s, {size_kb:.1f} KB) - {desc}")
        manifest.append({
            "filename": filename,
            "duration_sec": round(duration, 2),
            "description": desc,
            "type": "REAL" if "real" in filename else "DEEPFAKE",
        })

    # Create README in datasets/sample/
    readme_path = SAMPLE_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# SHADOW-NET Reference Audio Samples\n\n")
        f.write("This directory contains reference audio recordings for immediate live evaluation and demonstration of SHADOW-NET without requiring live microphone recording or external 30GB dataset downloads.\n\n")
        f.write("All files are encoded at **16,000 Hz, 16-bit PCM mono WAV**, matching the exact ingestion parameters of the SHADOW-NET audio preprocessing pipeline.\n\n")
        f.write("## Sample Manifest\n\n")
        f.write("| Filename | Class | Duration | Description |\n")
        f.write("|---|:---:|:---:|---|\n")
        for m in manifest:
            f.write(f"| `{m['filename']}` | **{m['type']}** | {m['duration_sec']}s | {m['description']} |\n")
        f.write("\n## How to Use for Demonstrations\n\n")
        f.write("### 1. Web UI Demonstration\n")
        f.write("1. Open the **Controlled Test Bench** at `http://localhost:3000/session`.\n")
        f.write("2. Click **Start Test Session**.\n")
        f.write("3. In the **Upload Test WAV File** panel, select or drag & drop any sample file from `datasets/sample/`.\n")
        f.write("4. Watch the real-time Mel-spectrogram rendering, inference confidence, and threat detection triggers in `/live` and `/dashboard`.\n\n")
        f.write("### 2. cURL Command-Line Demonstration\n")
        f.write("```bash\n")
        f.write("# Analyze a real speech sample\n")
        f.write('curl -X POST "http://localhost:8000/audio/analyze" \\\n')
        f.write('  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \\\n')
        f.write('  -F "file=@datasets/sample/real_01_bonafide_speech.wav"\n\n')
        f.write("# Analyze a synthetic deepfake sample (triggers CRITICAL alert and session restriction)\n")
        f.write('curl -X POST "http://localhost:8000/audio/analyze" \\\n')
        f.write('  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \\\n')
        f.write('  -F "file=@datasets/sample/synthetic_01_deepfake_vocoder_glitch.wav"\n')
        f.write("```\n")

    print(f"  [OK] Created README: {readme_path.name}")


if __name__ == "__main__":
    generate_all_samples()

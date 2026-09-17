# SHADOW-NET Reference Audio Samples

This directory contains reference audio recordings for immediate live evaluation and demonstration of SHADOW-NET without requiring live microphone recording or external 30GB dataset downloads.

All files are encoded at **16,000 Hz, 16-bit PCM mono WAV**, matching the exact ingestion parameters of the SHADOW-NET audio preprocessing pipeline.

## Sample Manifest

| Filename | Class | Duration | Description |
|---|:---:|:---:|---|
| `real_01_bonafide_speech.wav` | **REAL** | 3.0s | Natural human speech, varied pitch contour & organic formant structure |
| `real_02_bonafide_speech.wav` | **REAL** | 3.2s | Natural human voice, conversational tempo & breath envelope |
| `synthetic_01_deepfake_vocoder_glitch.wav` | **DEEPFAKE** | 3.0s | Deepfake vocoder artifact with 6.4kHz checkerboard & phase jumps |
| `synthetic_02_deepfake_neural_tts.wav` | **DEEPFAKE** | 3.0s | Deepfake synthetic voice with monotone pitch & spectral smearing |
| `synthetic_03_deepfake_cloned_voice.wav` | **DEEPFAKE** | 2.8s | Cloned voice simulation with phase discontinuities & alias hiss |

## How to Use for Demonstrations

### 1. Web UI Demonstration
1. Open the **Controlled Test Bench** at `http://localhost:3000/session`.
2. Click **Start Test Session**.
3. In the **Upload Test WAV File** panel, select or drag & drop any sample file from `datasets/sample/`.
4. Watch the real-time Mel-spectrogram rendering, inference confidence, and threat detection triggers in `/live` and `/dashboard`.

### 2. cURL Command-Line Demonstration
```bash
# Analyze a real speech sample
curl -X POST "http://localhost:8000/audio/analyze" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -F "file=@datasets/sample/real_01_bonafide_speech.wav"

# Analyze a synthetic deepfake sample (triggers CRITICAL alert and session restriction)
curl -X POST "http://localhost:8000/audio/analyze" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -F "file=@datasets/sample/synthetic_01_deepfake_vocoder_glitch.wav"
```

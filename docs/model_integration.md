# SHADOW-NET Model Integration Guide: ResNet-18 Checkpoint Loading

This guide explains how machine learning weights are loaded into SHADOW-NET, how to drop in a trained model checkpoint (`resnet18.pth`), and how the application behaves before and after weights exist.

---

## 🎯 Architecture Overview

SHADOW-NET uses a swappable `DetectorInterface` decoupled from the rest of the audio pipeline.

```
Incoming Audio (WAV/base64)
           │
           ▼
 [Audio Preprocessing] ── (16kHz Mono Normalized)
           │
           ▼
 [Voice Activity Detection] ── (EnergyVAD / SileroVAD)
           │
           ▼
 [Rolling Window Slicing] ── (2.0s windows, 1.0s hop)
           │
           ▼
 [Log-Mel-Spectrograms] ── (n_mels=128, n_fft=1024)
           │
           ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                       MODEL FACTORY                         │
 │                                                             │
 │   Does `model/resnet18.pth` exist and `DEMO_MODE=false`?    │
 │            ├── YES ──► ResNet18AudioClassifier (mode="ml")  │
 │            └── NO  ──► DemoFallbackDetector (mode="demo")   │
 └─────────────────────────────────────────────────────────────┘
           │
           ▼
   [Decision Engine] ──► (REAL / DEEPFAKE / UNCERTAIN)
```

---

## ⚖️ Behavior: Before vs. After Model Checkpoint

| Attribute | Before Checkpoint (`model/resnet18.pth` absent) | After Checkpoint (`model/resnet18.pth` present) |
| :--- | :--- | :--- |
| **Active Detector** | `DemoFallbackDetector` | `ResNet18AudioClassifier` |
| **Operational Mode** | `"demo"` | `"ml"` |
| **Console Warning** | Emits visible warning on startup | Logs successful model checkpoint load |
| **Frontend UI** | Prominent amber **`[DEMO MODE]`** badge displayed | Green **`[ML LIVE]`** badge displayed |
| **Predictions** | Plausible deterministic synthetic heuristics | Real neural tensor forward pass through ResNet-18 |
| **Risk / Decisions** | Fully simulated risk lifecycle | Validated acoustic deepfake classification |

---

## 📥 How to Drop in `resnet18.pth`

Phase 7 of SHADOW-NET contains the offline training pipeline (`training/train_resnet18.py`) which trains on dataset benchmarks (e.g., ASVspoof / WaveFake) and produces the optimal model weights.

### Step-by-Step Installation:
1. Place the checkpoint file at:
   ```
   shadow-net/model/resnet18.pth
   ```
2. Check your `.env` configuration:
   ```env
   MODEL_PATH=../model/resnet18.pth
   DEMO_MODE=false
   ```
3. Checkpoint format requirements:
   - **Backbone**: PyTorch `torchvision.models.resnet18`
   - **First Layer (`conv1`)**: `Conv2d(in_channels=1, out_channels=64, kernel_size=7, stride=2, padding=3, bias=False)`
   - **Output Layer (`fc`)**: `Linear(in_features=512, out_features=2)` (Index 0: Real, Index 1: Deepfake)
   - **Format**: Standard PyTorch `state_dict` dictionary.
4. Restart or call the detector reload helper. The backend will automatically log:
   ```
   [INFO] Model file detected at: .../model/resnet18.pth. Initializing ResNet-18 classifier.
   [INFO] ResNet-18 model weights loaded successfully.
   ```
   All API endpoints and WebSocket streams will immediately start returning `"mode": "ml"`.

# SHADOW-NET: Real-Time Deepfake Voice Interception & Forensic Evaluation Prototype

SHADOW-NET is an experimental cybersecurity and audio forensic evaluation prototype designed to detect synthesized, cloned, and vocoder-manipulated speech in real-time. It analyzes streaming audio, extracts acoustic representations (log-Mel spectrograms and MFCCs), evaluates synthetic voice probabilities through neural classifiers, and orchestrates automated security response actions (session restriction and out-of-band identity verification).

> [!IMPORTANT]
> **Controlled Testing Environment Notice**:
> SHADOW-NET is engineered exclusively for controlled, user-initiated test sessions (e.g. microphone capture or WAV audio upload within self-owned test benches). It **does NOT** intercept, eavesdrop on, or tap into third-party VoIP, Zoom, Microsoft Teams, WebRTC, or carrier telephony infrastructure. Audio is processed transiently in-memory; raw recordings are **never stored** unless explicitly authorized by the operator.

---

## 🏛️ System Architecture

```
                                    +------------------------------------------+
                                    |         Controlled Audio Ingestion       |
                                    |   (Microphone Stream / Test WAV Upload)  |
                                    +--------------------+---------------------+
                                                         |
                                                         v
                                    +------------------------------------------+
                                    |     Acoustic Preprocessing Pipeline      |
                                    |    - Resampling to 16 kHz Mono           |
                                    |    - Amplitude Normalization             |
                                    |    - Silero Voice Activity Detection     |
                                    |    - 2.0s Rolling Windows (1.0s stride)  |
                                    +--------------------+---------------------+
                                                         |
                                                         v
                                    +------------------------------------------+
                                    |        Feature Extraction (Librosa)      |
                                    |    - Log-Mel Spectrogram (128 bands)     |
                                    |    - MFCC Features (20 cepstral bins)    |
                                    +--------------------+---------------------+
                                                         |
                            +----------------------------+----------------------------+
                            |                                                         |
                            v                                                         v
        +---------------------------------------+         +---------------------------------------+
        |        Production ML Classifier       |         |        Deterministic Demo Fallback    |
        |   - ResNet-18 (1-Channel Spectrogram) |   OR    |   - Synthetic Heuristic Simulator     |
        |   - Binary: Bonafide vs. Deepfake     |         |   - Visible DEMO MODE Badge & Alert   |
        |   - Sub-50ms Inference Latency        |         |   - Safe for CI / Testing             |
        +-------------------+-------------------+         +-------------------+-------------------+
                            |                                                 |
                            +----------------------------+--------------------+
                                                         |
                                                         v
                                    +------------------------------------------+
                                    |             Decision Engine              |
                                    |   - Threat Scoring: LOW / MED / CRITICAL |
                                    |   - Real-Time WebSocket Telemetry        |
                                    |   - Automated Session Restriction        |
                                    |   - Prototype MFA Challenge Recovery     |
                                    +--------------------+---------------------+
                                                         |
                                    +--------------------+---------------------+
                                    |                                          |
                                    v                                          v
                    +-------------------------------+          +-------------------------------+
                    |     Next.js SOC Frontend      |          |       MongoDB Persistence     |
                    |   - Live Waveform & Spectrum  |          |   - User & Session Records    |
                    |   - Real-Time Threat Badges   |          |   - Forensic Incident Audit   |
                    |   - Interactive MFA Terminal  |          |   - Dynamic System Settings   |
                    +-------------------------------+          +-------------------------------+
```

---

## 📁 Repository Layout

```
shadow-net/
├── backend/                       # FastAPI asynchronous backend service
│   ├── app/
│   │   ├── audio/                 # Preprocessing, Silero VAD, Feature extraction
│   │   ├── core/                  # Security utilities & logging configuration
│   │   ├── ml/                    # Classifier interface, ResNet-18, Demo fallback
│   │   ├── models/                # Pydantic & MongoDB document schemas
│   │   ├── routers/               # /auth, /session, /audio, /incidents, /verify
│   │   ├── services/              # Incident management & forensic logic
│   │   ├── config.py              # Pydantic Settings & environment binding
│   │   └── db.py                  # Motor MongoDB client with mock fallback
│   ├── Dockerfile                 # Backend container definition
│   ├── requirements.txt           # Production backend dependencies
│   └── main.py                    # Application entrypoint & ASGI lifespan
├── frontend/                      # Next.js 14+ (App Router), TypeScript, Tailwind CSS
│   ├── src/
│   │   ├── app/                   # App routes: /, /session, /live, /dashboard, etc.
│   │   ├── components/            # UI widgets: Spectrum, Waveform, ThreatBadge
│   │   └── lib/                   # API client, WebSocket hook, Auth context
│   ├── Dockerfile                 # Multi-stage Next.js production build
│   └── package.json               # Node dependencies
├── datasets/                      # Reference audio & training data
│   └── sample/                    # Pre-generated 16kHz WAV test audio files
│       ├── real_01_bonafide_speech.wav
│       ├── real_02_bonafide_speech.wav
│       ├── synthetic_01_deepfake_vocoder_glitch.wav
│       ├── synthetic_02_deepfake_neural_tts.wav
│       ├── synthetic_03_deepfake_cloned_voice.wav
│       └── README.md
├── training/                      # Isolated model training & evaluation pipeline
│   ├── dataset_prep.py            # ASVspoof / WaveFake ingestion & synthetic generator
│   ├── dataset.py                 # PyTorch Dataset ensuring feature parity
│   ├── models.py                  # CNN Baseline and adapted ResNet-18 models
│   ├── train.py                   # Multi-epoch trainer with complete metric matrix
│   ├── evaluate.py                # Latency SLA benchmark & 7-perturbation stress suite
│   └── requirements-training.txt  # Training-only dependencies
├── model/                         # Checkpoint directory (e.g. resnet18.pth)
├── scripts/                       # Verification test runners (Phases 1 through 8)
├── docker-compose.yml             # Local multi-service orchestration
└── .env.example                   # Environment variable template
```

---

## ⚡ Quickstart with Docker Compose (Recommended)

The easiest way to launch the complete SHADOW-NET stack (MongoDB, FastAPI Backend, and Next.js Frontend) is using Docker Compose:

### 1. Clone & Prepare Environment
```bash
git clone https://github.com/himesh-mehta/shadow-net.git
cd shadow-net
cp .env.example .env
```

### 2. Launch Stack
```bash
docker-compose up --build
```

### 3. Access Services
- **Web User Interface**: `http://localhost:3000`
- **FastAPI Interactive Docs (Swagger)**: `http://localhost:8000/docs`
- **Backend Health Check**: `http://localhost:8000/health`
- **MongoDB**: `localhost:27017`

---

## 🛠️ Manual Installation & Local Development

If running outside Docker, follow the steps below for Windows or Linux.

### Prerequisites
- **Python**: 3.10 or 3.11 (PyTorch CPU wheels tested)
- **Node.js**: 18.x or 20.x
- **MongoDB**: 7.x (or utilize the automatic zero-setup in-memory fallback)

---

### Step 1: Environment Configuration
Copy the template configuration file in the project root:
```bash
# Windows (PowerShell) / Linux
cp .env.example .env
```

---

### Step 2: Backend Setup

#### On Windows:
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### On Linux / macOS:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

*Note: On Linux, ensure `libsndfile1` and `ffmpeg` are installed (`sudo apt-get install libsndfile1 ffmpeg`).*

---

### Step 3: Frontend Setup

In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

### Step 4: MongoDB Options

1. **Automatic In-Memory Mock (Zero Setup)**:
   If MongoDB is not running locally, the backend automatically detects connection failure, logs a notice, and boots an internal `mongomock-motor` instance. Everything works out-of-the-box without installing MongoDB.
2. **Local MongoDB Service**:
   - **Windows**: Install MongoDB Community Edition as a Windows Service.
   - **Linux**: `sudo systemctl start mongod`
3. **Docker MongoDB**:
   ```bash
   docker run -d --name shadow-net-mongo -p 27017:27017 -v mongo_data:/data/db mongo:7.0
   ```

---

## ⚙️ Environment Variables Reference

| Variable | Default Value | Description |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017/shadow_net` | MongoDB connection connection URI |
| `JWT_SECRET` | *(64-char string)* | Cryptographic key used to sign session JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT token validity window (8 hours) |
| `DETECTION_THRESHOLD` | `0.75` | Probability cutoff (0.0–1.0) to classify as DEEPFAKE |
| `AUDIO_SAMPLE_RATE` | `16000` | Standard pipeline audio sampling rate in Hz |
| `AUDIO_WINDOW_SECONDS` | `2.0` | Duration of each rolling analysis window |
| `VAD_SENSITIVITY` | `2` | Silero Voice Activity Detector aggressiveness (0–3) |
| `DEMO_MODE` | `true` | Toggle between synthetic demo fallback and loaded weights |
| `MODEL_PATH` | `../model/resnet18.pth` | Relative or absolute path to model checkpoint |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend backend API URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | Frontend WebSocket telemetry URL |

---

## 🤖 Demo Mode vs. Production ML Mode

SHADOW-NET is built with clear architectural separation between demonstration mode and production neural inference:

### Mode Comparison

| Feature | Demo Mode (`DEMO_MODE=true` or no weights) | Production ML Mode (`DEMO_MODE=false` + weights) |
|---|---|---|
| **Classifier** | `DemoFallbackDetector` (Heuristic/Synthetic) | `ResNet18AudioClassifier` (Adapted 1-Ch ResNet-18) |
| **Model Weights** | None required | Loaded from `model/resnet18.pth` |
| **UI Header Badge** | Amber: **`DEMO MODE`** | Emerald: **`ML LIVE`** |
| **API Response Field** | `"mode": "demo"`, `"is_synthetic": true` | `"mode": "ml"`, `"is_synthetic": false` |
| **Inference Latency** | Simulated (~15ms) | Measured CPU/GPU execution (~11ms) |

### Switching to Production ML Mode
1. Train a model using Phase 7 scripts:
   ```bash
   python training/train.py --model resnet18 --epochs 5 --output-model model/resnet18.pth
   ```
2. Ensure the checkpoint file exists at `model/resnet18.pth`.
3. Set `DEMO_MODE=false` in `.env` (or via the UI at `/settings` as an Administrator).
4. Restart or reload the backend. The header badge will immediately transition to **`ML LIVE`**.

---

## 🎧 Out-of-the-Box Demo with Sample Audio

To test the system immediately without training a model or recording live audio:

1. Open `http://localhost:3000` and sign in with the preset Administrator role (`alex.vance` / `admin123456`).
2. Navigate to **Controlled Test Bench** (`/session`).
3. Click **Start Test Session**.
4. Drag & drop any of the reference WAV files located under `datasets/sample/`:
   - `real_01_bonafide_speech.wav`: Natural speech. Verdict remains **REAL** with low threat.
   - `synthetic_01_deepfake_vocoder_glitch.wav`: Deepfake artifacts. Triggers **DEEPFAKE**, CRITICAL threat alert, and locks the session into **RESTRICTED** state.
5. In the alert banner, click **Initiate Identity Verification** (`/verify`).
6. Click **Request Prototype OTP**, enter the generated 6-digit code, and click **Submit Verification Code**.
7. The session is restored to **ACTIVE** state.

---

## 🎙️ Browser Microphone Permissions Note

When testing real-time microphone capture on the `/session` screen:
- **Security Context Requirement**: Modern web browsers only grant microphone access (`navigator.mediaDevices.getUserMedia`) in **secure contexts**:
  - `http://localhost:3000` (Localhost is treated as secure by default)
  - `https://...` (Valid SSL/TLS certificate required if accessing across a LAN or remote IP)
- If microphone access is denied by browser settings, a clear warning is displayed and you can immediately use the **Upload Test WAV File** option instead.

---

## 📡 Example API Commands (`curl`)

### 1. Authenticate Operator
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "alex.vance", "password": "admin123456"}'
```
*Response returns `{ "access_token": "<TOKEN>", "token_type": "bearer", "role": "Administrator" }`.*

### 2. Start a Controlled Test Session
```bash
curl -X POST "http://localhost:8000/session/start" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"client_label": "Terminal Audio Source", "store_audio": false}'
```

### 3. Analyze Audio File
```bash
curl -X POST "http://localhost:8000/audio/analyze" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@datasets/sample/synthetic_01_deepfake_vocoder_glitch.wav"
```

### 4. Query Security Incidents
```bash
curl -X GET "http://localhost:8000/incidents" \
  -H "Authorization: Bearer <TOKEN>"
```

### 5. Request & Submit Prototype OTP
```bash
# Request OTP
curl -X POST "http://localhost:8000/verify/request-otp" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<SESSION_ID>"}'

# Verify Code
curl -X POST "http://localhost:8000/verify" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<SESSION_ID>", "otp_code": "123456"}'
```

---

## 🔍 Troubleshooting Guide

### 1. MongoDB Not Connecting
- **Symptom**: Console outputs `[WARNING] Live MongoDB unreachable... Falling back to in-memory AsyncMongoMockClient`.
- **Cause**: No MongoDB daemon is active at `mongodb://localhost:27017`.
- **Resolution**: This is an intended, safe fallback for quick developer testing. To use live persistent MongoDB, start MongoDB via Docker (`docker run -d -p 27017:27017 mongo:7.0`) or start the local service (`sudo systemctl start mongod`).

### 2. Microphone Not Available
- **Symptom**: Browser shows `Microphone access denied or not supported`.
- **Cause**: Browser permissions are blocked or accessing the site via an unsecured non-localhost IP (`http://192.168.x.x:3000`).
- **Resolution**: Access via `http://localhost:3000` or enable microphone permissions in your browser URL bar. Alternatively, use the built-in WAV file upload.

### 3. WebSocket Disconnected / Telemetry Offline
- **Symptom**: Top navigation bar reports `TELEMETRY: OFFLINE`.
- **Cause**: The backend is not running on port 8000 or firewall blocked WebSocket upgrade requests.
- **Resolution**: Ensure backend is running (`uvicorn main:app --port 8000`). Check browser console for connection refused errors. The frontend automatically attempts reconnection with backoff.

### 4. Demo Mode vs. ML Mode Confusion
- **Symptom**: The UI consistently reports `DEMO MODE` even after starting.
- **Cause**: `DEMO_MODE=true` is set in `.env` or no valid checkpoint was found at `model/resnet18.pth`.
- **Resolution**: Run `python scripts/verify_phase7.py` to generate a trained checkpoint, then update `.env` to `DEMO_MODE=false`. Verify at `http://localhost:3000/settings`.

---

## 🔒 Security & Privacy Commitments

1. **No Raw Audio Retention**: By default, `store_audio` is strictly `False`. Audio waveforms are analyzed transiently in volatile RAM and discarded.
2. **Zero Third-Party Telephony Interception**: SHADOW-NET is restricted to operator-controlled test sessions; no hooks or network interfaces connect to Zoom, Teams, WebRTC gateways, or PSTN switches.
3. **Explicit Synthetic Labeling**: Any predictions originating from demo fallbacks or synthetic generators are unmistakably badged in both API metadata (`mode: "demo"`) and UI elements.
4. **Credential Safety**: Passwords are encrypted with bcrypt; JWT signing secrets must be set via environment variables.

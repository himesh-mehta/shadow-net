# SHADOW-NET: Real-Time Deepfake Voice Interception Prototype

SHADOW-NET is an experimental deepfake voice detection and session response prototype. It analyzes incoming audio streams in real-time, extracts acoustic features (MFCCs and Mel-Spectrograms), evaluates synthetic voice probabilities via a classifier, and orchestrates risk-mitigation flows (session restriction and identity verification).

> [!IMPORTANT]
> **Controlled Testing Environment Notice**:
> SHADOW-NET is built exclusively for controlled, user-initiated test sessions (e.g. microphone input or WAV audio upload within self-owned test benches). It **does NOT** intercept, eavesdrop on, or tap into third-party VoIP, Zoom, Microsoft Teams, or carrier telephony infrastructure.

---

## 🏛️ Project Architecture

```
shadow-net/
├── frontend/          # Next.js 14+ (App Router), TypeScript, Tailwind CSS, Recharts
├── backend/           # FastAPI, Uvicorn, Motor (MongoDB), Librosa, PyTorch
├── model/             # Checkpoint weights (e.g. resnet18.pth)
├── training/          # Offline model training & evaluation scripts
├── datasets/          # Training/evaluation speech datasets (gitignored)
├── scripts/           # Pipeline sanity checks and helper tools
├── docs/              # System specifications and phase documentation
├── docker-compose.yml # Orchestration for MongoDB, Backend, and Frontend
└── .env.example       # Template environment variables
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: v18.17+ (v20+ recommended)
- **Python**: 3.10 or 3.11 (with PyTorch and audio dependencies support)
- **MongoDB**: Local MongoDB instance or Docker daemon

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set the required environment variables:
- `MONGODB_URI`: Local MongoDB URI (default: `mongodb://localhost:27017/shadow_net`)
- `JWT_SECRET`: Secret key for session/user token generation
- `DETECTION_THRESHOLD`: Confidence threshold to trigger deepfake response (e.g., `0.75`)
- `DEMO_MODE`: `true` (uses fallback synthetic detector) or `false` (requires PyTorch weights)

### 3. Local MongoDB Setup
You can run MongoDB locally using Docker:
```bash
docker run -d --name shadow-net-mongo -p 27017:27017 -v mongo_data:/data/db mongo:7.0
```
Or start the stack via docker compose:
```bash
docker-compose up mongodb -d
```

### 4. Running the Backend
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Check health: `http://localhost:8000/health`

### 5. Running the Frontend
```bash
cd frontend
npm install
npm run dev
```
Access UI: `http://localhost:3000`

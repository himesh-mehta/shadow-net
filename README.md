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
│   ├── app/
│   │   ├── config.py       # Pydantic Settings
│   │   ├── db.py           # Async Motor connection & mock fallback
│   │   ├── models/         # User, Session, Incident, Settings schemas
│   │   └── routers/        # /auth, /session, /settings, /incidents
│   └── main.py             # App entrypoint and lifespan manager
├── model/             # Checkpoint weights (e.g. resnet18.pth)
├── training/          # Offline model training & evaluation scripts
├── datasets/          # Training/evaluation speech datasets (gitignored)
├── scripts/           # Pipeline sanity checks and verification scripts
├── docs/              # System specifications and phase documentation
├── docker-compose.yml # Orchestration for MongoDB, Backend, and Frontend
└── .env.example       # Template environment variables
```

---

## 🗄️ Running MongoDB Locally & Setting Up `.env`

SHADOW-NET utilizes MongoDB via the asynchronous `motor` driver for persistent storage of users, sessions, settings, and incidents.

### 1. Configure `.env`
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```
Key configuration settings:
```env
MONGODB_URI=mongodb://localhost:27017/shadow_net
JWT_SECRET=your_super_secret_64_char_random_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
DETECTION_THRESHOLD=0.75
DEMO_MODE=true
```

### 2. Option A: Docker (Recommended)
Run a MongoDB 7 container locally:
```bash
docker run -d --name shadow-net-mongo -p 27017:27017 -v mongo_data:/data/db mongo:7.0
```
Or start via Docker Compose:
```bash
docker-compose up mongodb -d
```

### 3. Option B: Local MongoDB Service (Windows / Linux)
- **Windows**: Install [MongoDB Community Server](https://www.mongodb.com/try/download/community) and MongoDB Compass. MongoDB runs automatically as a Windows Service at `mongodb://127.0.0.1:27017`.
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo systemctl start mongod
  sudo systemctl status mongod
  ```

### 4. Zero-Setup Dev Fallback
If live MongoDB is not installed or running, the backend automatically logs a notice and initializes an in-memory `mongomock-motor` instance, enabling immediate development and test verification without a running database daemon.

---

## 🚀 Running the Backend

```bash
cd backend
# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Start Uvicorn ASGI server
uvicorn main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## 💻 Running the Frontend

```bash
cd frontend
npm install
npm run dev
```
- Access UI: `http://localhost:3000`

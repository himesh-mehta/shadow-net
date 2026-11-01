# SHADOW-NET — college audio deepfake prototype

An extension of the supplied SHADOW-NET project: Next.js interface, FastAPI backend,
local pretrained speech detector, and transparent evaluation. It analyzes uploaded
recordings and local microphone audio; it does not intercept phone or video calls.

**Start here.** Earlier project documentation is preserved in
[docs/ORIGINAL_README.md](docs/ORIGINAL_README.md). Its ResNet/demo claims and setup
are historical; the instructions below apply to this version.

## What changed

- Pinned pretrained Wav2Vec2-XLSR detector, replacing the toy-trained ResNet as the ML default.
- Raw 16 kHz mono waveform input; Mel/MFCC arrays are for visualization and acoustic observations.
- Class mapping read from the checkpoint (never assumes a real/fake index order).
- Demo/ML selection reaches the detector and reloads it. Missing weights produce an explicit error.
- REST, SSE and WebSocket paths carry consistent mode, model status, score and verdict fields.
- Frontend API/auth/WebSocket helpers restored; the generic `lib/` ignore rule previously excluded them.
- Mock-database demo users seeded on startup; temporary data resets when the backend restarts.
- Microphone chunks encoded as independent PCM WAVs instead of undecodable WebM fragments.
- Best and last training checkpoints saved separately; unreadable training audio raises an error.
- Evaluation recognizes `AI_SUSPECTED`, passes model status correctly, and reports model identity.
- Repository oscillator samples remain available only for pipeline checks.

## Setup on Windows (recommended: Python 3.12, Node 20+)

Extract this ZIP into a **new folder**, retaining your original project as a backup.
Open a terminal at the extracted project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r backend/requirements-prototype.txt
Copy-Item .env.example .env
python scripts/download_detector.py
```

If PowerShell prevents activation, use `.venv\Scripts\python.exe` in place of `python`.
On Linux/macOS, create the environment with `python3 -m venv .venv` and activate
with `source .venv/bin/activate`.

The one-time model download is approximately **1.3 GB**. It is deliberately excluded
from the small source ZIP. No Hugging Face API key is needed for this public model.
The download script checks that the pinned model loads. Subsequent inference uses
cached files (`HF_LOCAL_FILES_ONLY=true`) and does not upload audio to a model service.

The supplied `.env.example` selects ML mode. A project with no `.env` defaults to demo
mode. Do not copy credentials into chat or commit your `.env`.

Start backend, from the project root:

```powershell
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. API status: http://127.0.0.1:8000/health.
The status response includes the **actually loaded** model and operating mode.

## First demonstration

1. If no MongoDB is running, the app uses temporary in-memory storage and seeds demo users.
2. Quick-login as Administrator (`alex.vance` / `admin123456`). These are public demonstration credentials.
3. Visit Settings and confirm the pretrained model is loaded. Turning ML on fails visibly if model files are missing.
4. Upload a 3–10 second speech WAV on `/session`. The prototype accepts 0.5–60 seconds.
5. Compare a genuine human recording and actual AI-generated speech. Preserve and discuss incorrect results too.
6. Check the model name, verdict and AI score. Suspected AI produces a prototype incident; critical scores can restrict the local session.
7. Demo mode always displays uncertain. It does not simulate accurate detection.

If you use your own persistent MongoDB, register your own demo account through
`/docs`; automatic seeding is restricted to the temporary mock database.
Microphone capture requires localhost or HTTPS. Physical microphone behavior still
needs testing on your own browser and hardware; prefer WAV uploads for the first demo.

## Selected pretrained model

- Model: [Gustking/wav2vec2-large-xlsr-deepfake-audio-classification](https://huggingface.co/Gustking/wav2vec2-large-xlsr-deepfake-audio-classification)
- Revision: `f7050b586236dc910d1157f430def2d0647b02b4`
- Architecture: `Wav2Vec2ForSequenceClassification` (XLSR, approximately 300M parameters).
- Publisher-listed license: Apache-2.0; retain attribution and consult the upstream terms.
- Input: 16 kHz mono waveform, using the checkpoint's feature extractor and normalization.
- Label mapping: index 0 = real, index 1 = fake, verified against downloaded config.
- Default analysis windows: 4 seconds with 2-second hop. This is a prototype integration choice, not a validated optimum.
- CPU threads: 2 by default; adjust `CPU_THREADS` for your computer.

The author's card reports evaluation on ASVspoof2019, but does not fully document
all training data or language coverage. **Do not describe this as our measured accuracy
or claim support for Hindi/Marathi without testing.**

A smaller MelodyMachine candidate was also tried and rejected because it missed
both AI clips in the smoke test. The comparison and exact observed outputs are in
[docs/PROTOTYPE_VALIDATION.md](docs/PROTOTYPE_VALIDATION.md).

## What the scores mean

“AI score” is an **uncalibrated softmax score**, not a measured probability that the
recording is fake. A final score below 0.35 means REAL, 0.35–0.65 is UNCERTAIN, and
0.65 or above is AI_SUSPECTED. The settings slider overrides these bands symmetrically
(e.g. 0.75 gives bands at 0.25 and 0.75). These thresholds have not been calibrated
on your recordings.

The final score is a heuristic aggregation (60% maximum window score + 40% mean),
with sustained-window handling inherited from the original project. VAD telemetry
is retained, but pretrained inference keeps the waveform intact instead of joining
speech intervals. Spectral measurements are heuristic acoustic observations, not
causal explanations of this model or proof of manipulation. OTP recovery remains
an explicitly simulated college feature.

## Evaluate your own recordings

Create a folder of actual speech WAVs. Name known genuine files `real_*.wav` and
known generated files `fake_*.wav`. Names provide ground-truth labels **only for
evaluation**, not model input. Use multiple speakers and generators, and keep
final evaluation recordings separate from examples used to choose settings.

```powershell
python scripts/check_recordings.py path/to/recordings --output scripts/evaluation_report.json
```

Refresh `/evaluation` to view the report. The dashboard's built-in Run button uses
the original mathematical samples; its banner explicitly identifies this as a
pipeline check, not a human-speech benchmark.

## Verification

```powershell
python -m pip install pytest scikit-learn
python -m pytest tests -q
cd frontend
npm run build
```

Tests use controlled detector doubles for regression checks; they do not measure
speech detection accuracy. See the separate real-model API smoke-test observations
in the validation document. Dependency deprecation warnings remain in the inherited
backend. No real-user speech or external model weights are bundled.

## Attribution

This version extends the supplied SHADOW-NET source archive, commit
`45e4801fbb351ca72c6cd60692f5bbc874a9c81b`. The user identified
[VoiceGuard](https://github.com/MohammadThabetHassan/VoiceGuard) as the original
inspiration; an exact upstream code comparison has not been performed here.
No project-level LICENSE file was present in the supplied archive. Confirm original
authorship and licensing before publishing this code. Credit the model author
separately and describe your contribution as integration, evaluation and application fixes.

"""Regression checks for mode switching, class mapping and API verdict consistency."""
import asyncio
import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from main import app
from app.db import get_db
from app.config import get_settings
from app.ml import factory
from app.ml.pretrained import DetectorUnavailable, resolve_fake_index
from app.ml.decision import DecisionEngine
from app.routers.auth import get_current_user
from app.models.user import UserInDB


class FakeWaveformDetector:
    name, version, mode, model_status = "test-only-detector", "test", "ml", "TRAINED"
    is_loaded = is_trained = uses_waveform = True
    is_heuristic_placeholder = False
    def __init__(self, *args, **kwargs): pass
    def predict_audio(self, audio, sr=16000, **kwargs):
        assert audio.ndim == 1 and sr == 16000
        return {"fake_probability": 0.9, "ai_probability": 0.9, "real_probability": 0.1}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(factory, "_CURRENT_DETECTOR", None)
    monkeypatch.setattr(factory, "_CURRENT_KEY", None)
    monkeypatch.setattr(factory, "_LAST_ERROR", None)
    monkeypatch.setattr(factory, "PretrainedAudioDetector", FakeWaveformDetector)
    monkeypatch.setattr(get_settings(), "DEMO_MODE", True)
    monkeypatch.setattr(get_settings(), "DETECTOR_BACKEND", "huggingface")
    db = AsyncMongoMockClient().test
    user = UserInDB(id="tester", username="tester", email="tester@example.com", hashed_password="unused", role="Administrator")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    # No lifespan: isolates tests from external MongoDB and model downloads.
    with TestClient(app) as c:
        # Lifespan connects separately, but route overrides remain isolated.
        yield c, db
    app.dependency_overrides.clear()


def wav(silence=False):
    data = np.zeros(48000, dtype=np.float32) if silence else (0.3 * np.sin(np.arange(48000) * 0.1)).astype(np.float32)
    out = io.BytesIO(); sf.write(out, data, 16000, format="WAV")
    return out.getvalue()


def stream_events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_label_mapping():
    assert resolve_fake_index({0: "fake", 1: "real"}) == 0
    assert resolve_fake_index({0: "bonafide", 1: "spoof"}) == 1
    with pytest.raises(DetectorUnavailable): resolve_fake_index({0: "LABEL_0", 1: "LABEL_1"})


def test_demo_never_loads_checkpoint(client):
    c, _ = client
    result = c.post("/audio/analyze", files={"file": ("fake.wav", wav(), "audio/wav")})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["prediction"] == "UNCERTAIN"
    assert body["mode"] == "demo" and body["model_status"] == "NOT_TRAINED"
    assert not factory.detector_status()["loaded"]


def test_toggle_and_rest_sse_parity(client):
    c, _ = client
    switched = c.put("/settings", json={"demo_mode": False, "detection_threshold": 0.65})
    assert switched.status_code == 200, switched.text
    assert get_settings().DEMO_MODE is True  # DB setting must override unchanged env default.
    rest = c.post("/audio/analyze", files={"file": ("human.wav", wav(), "audio/wav")}).json()
    events = stream_events(c.post("/audio/analyze/stream", files={"file": ("anything.wav", wav(), "audio/wav")}))
    final = events[-1]
    assert final["type"] == "session_verdict", final
    for field in ("prediction", "display_verdict", "ai_probability", "mode", "model_status", "model_name"):
        assert rest[field] == final[field]
    assert rest["prediction"] == "AI_SUSPECTED" and rest["model_status"] == "TRAINED"
    assert c.get("/health").json()["detector"]["loaded"]
    assert c.put("/settings", json={"demo_mode": True}).status_code == 200
    assert factory.detector_status()["mode"] == "demo"


def test_failed_mode_switch_does_not_persist_or_predict(client, monkeypatch):
    c, db = client
    def fail(*args, **kwargs): raise DetectorUnavailable("test checkpoint missing")
    monkeypatch.setattr(factory, "PretrainedAudioDetector", fail)
    response = c.put("/settings", json={"demo_mode": False})
    assert response.status_code == 503
    assert asyncio.run(db.settings.find_one({"scope": "global"})) is None
    assert c.post("/audio/analyze", files={"file": ("x.wav", wav(), "audio/wav")}).json()["mode"] == "demo"
    asyncio.run(db.settings.update_one({"scope": "global"}, {"$set": {"demo_mode": False}}, upsert=True))
    assert c.post("/audio/analyze", files={"file": ("x.wav", wav(), "audio/wav")}).status_code == 503
    events = stream_events(c.post("/audio/analyze/stream", files={"file": ("x.wav", wav(), "audio/wav")}))
    assert events[-1]["type"] == "error" and not any(e["type"] == "session_verdict" for e in events)


def test_silence_is_an_input_error(client):
    c, _ = client
    response = c.post("/audio/analyze", files={"file": ("silence.wav", wav(True), "audio/wav")})
    assert response.status_code == 422


def test_aggregate_score_matches_decision():
    result = DecisionEngine().evaluate_session([{"ai_probability": 0.95}, {"ai_probability": 0.1}], model_status="TRAINED")
    assert result["prediction"].value == "AI_SUSPECTED"
    assert result["ai_probability"] >= 0.65


def test_websocket_uses_shared_pipeline(client, monkeypatch):
    c, db = client
    import app.routers.ws as ws
    monkeypatch.setattr(ws, "get_db", lambda: db)
    c.put("/settings", json={"demo_mode": False})
    with c.websocket_connect("/ws/detection/test-session") as connection:
        assert connection.receive_json()["type"] == "connection_established"
        connection.send_json({"type": "ping"})
        assert connection.receive_json()["type"] == "pong"
        connection.send_json({"type": "audio_chunk", "audio_base64": base64.b64encode(wav()).decode()})
        response = connection.receive_json()
        if response["type"] == "alert":
            response = connection.receive_json()
        assert response["type"] == "prediction_update", response
        assert response["prediction"] == "AI_SUSPECTED" and response["mode"] == "ml"


def test_evaluation_counts_ai_suspected_as_a_positive(client, tmp_path, monkeypatch):
    c, _ = client
    import app.routers.evaluation as evaluation
    monkeypatch.setattr(evaluation, "REPORT_PATH", tmp_path / "report.json")
    c.put('/settings', json={'demo_mode': False})
    (tmp_path / 'fake_recording.wav').write_bytes(wav())
    (tmp_path / 'real_recording.wav').write_bytes(wav())
    response = c.post('/evaluation/run', json={'audio_dir':str(tmp_path)})
    assert response.status_code == 200, response.text
    report = response.json()
    assert report['mode'] == 'ml' and report['model_status'] == 'TRAINED'
    assert report['confusion_matrix']['true_positives'] == 1
    assert report['confusion_matrix']['false_positives'] == 1
    assert report['summary']['recall'] == 1.0


def test_exact_window_does_not_add_a_duplicate_tail():
    from app.audio.features import slice_into_windows
    assert len(slice_into_windows(np.ones(32000, dtype=np.float32), window_sec=2.0, hop_sec=1.0)) == 1

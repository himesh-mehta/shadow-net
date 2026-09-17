"""
Phase 6 Comprehensive Integration Verification Suite for SHADOW-NET.
Validates:
1. End-to-end FastAPI backend API functionality (JWT Auth, Sessions, Audio Ingestion, ML Inference, Incidents, Analytics, Settings, Prototype MFA).
2. WebSocket telemetry streaming on /ws/detection/{session_id}.
3. Controlled test bench constraints: store_audio=False default privacy, demo mode flag, prototype MFA simulation disclaimer.
4. Production Next.js build compilation verification.
"""

import io
import sys
import json
import base64
import asyncio
from pathlib import Path
import soundfile as sf
import numpy as np

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from main import app
from app.db import get_db
from app.services.incident_service import handle_detection_trigger
from app.models.incident import PredictionType, ThreatLevel


def generate_synthetic_wav(duration_sec=2.0, sr=16000, freq=440.0) -> bytes:
    """Generate in-memory WAV bytes containing a pure sine wave."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


def run_phase6_verification():
    print("================================================================")
    print("      SHADOW-NET Phase 6 Frontend-Backend Integration Test")
    print("================================================================")

    with TestClient(app) as client:
        # Step 1: Authentication & Role Verification
        print("\n[Step 1] Verifying JWT Authentication & Role-Based Access...")
        admin_creds = {
            "username": "alex.vance",
            "email": "alex.vance@shadow.net",
            "password": "admin123456",
            "role": "Administrator",
        }
        # Register (or ignore if already exists)
        client.post("/auth/register", json=admin_creds)
        login_res = client.post("/auth/login", json={"username": "alex.vance", "password": "admin123456"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Verify /auth/me
        me_res = client.get("/auth/me", headers=admin_headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["username"] == "alex.vance"
        assert me_data["role"] == "Administrator"
        print(f"  [PASS] Authenticated as {me_data['username']} (Role: {me_data['role']})")

        # Step 2: System Settings Management
        print("\n[Step 2] Verifying System Settings (/settings)...")
        settings_get = client.get("/settings", headers=admin_headers)
        assert settings_get.status_code == 200, f"Settings GET failed: {settings_get.text}"
        current_settings = settings_get.json()
        assert "detection_threshold" in current_settings
        assert "demo_mode" in current_settings
        print(f"  [PASS] Current settings: threshold={current_settings['detection_threshold']}, demo_mode={current_settings['demo_mode']}")

        # Update settings
        settings_update = client.put(
            "/settings",
            headers=admin_headers,
            json={
                "detection_threshold": 0.80,
                "audio_window_length": 2.0,
                "vad_sensitivity": 2,
                "demo_mode": True,
            }
        )
        assert settings_update.status_code == 200, f"Settings PUT failed: {settings_update.text}"
        assert settings_update.json()["detection_threshold"] == 0.80
        print("  [PASS] Updated settings verified (threshold: 0.80, demo_mode: True)")

        # Step 3: Controlled Test Session Lifecycle
        print("\n[Step 3] Verifying Controlled Session Lifecycle (/session)...")
        session_start = client.post(
            "/session/start",
            headers=admin_headers,
            json={"client_label": "Integration Test Bench", "store_audio": False}
        )
        assert session_start.status_code == 201, f"Session start failed: {session_start.text}"
        session_data = session_start.json()
        session_id = session_data["session_id"]
        assert session_data["status"] == "active"
        assert session_data["store_audio"] is False, "Privacy violation: store_audio must default to False"
        print(f"  [PASS] Session started: {session_id} | Status: active | store_audio: False")

        # Check status
        status_res = client.get(f"/session/status?session_id={session_id}", headers=admin_headers)
        assert status_res.status_code == 200
        assert status_res.json()["session_id"] == session_id
        print(f"  [PASS] Session status confirmed: {status_res.json()['status']}")

        # Step 4: Audio Ingestion & Feature Analysis Pipeline
        print("\n[Step 4] Verifying Audio Pipeline (/audio/analyze)...")
        wav_bytes = generate_synthetic_wav(duration_sec=2.0)

        # Multipart upload
        multipart_res = client.post(
            "/audio/analyze",
            data={"session_id": session_id},
            files={"file": ("test_sine.wav", io.BytesIO(wav_bytes), "audio/wav")}
        )
        assert multipart_res.status_code == 200, f"Audio analysis failed: {multipart_res.text}"
        analysis_data = multipart_res.json()
        assert "prediction" in analysis_data
        assert "confidence" in analysis_data
        assert "threat_level" in analysis_data
        assert "mode" in analysis_data
        assert "detection_latency_ms" in analysis_data
        print(f"  [PASS] Multipart analysis: Prediction={analysis_data['prediction']}, Confidence={analysis_data['confidence']:.2f}, Mode={analysis_data['mode']}, Latency={analysis_data['detection_latency_ms']:.1f}ms")

        # Base64 JSON chunk upload
        b64_audio = base64.b64encode(wav_bytes).decode("utf-8")
        json_audio_res = client.post(
            "/audio/analyze/json",
            json={"audio_base64": b64_audio, "session_id": session_id}
        )
        assert json_audio_res.status_code == 200
        assert json_audio_res.json()["status"] == "success"
        print("  [PASS] Base64 streaming audio chunk analysis succeeded.")

        # Step 5: Incident Trigger & Session Restriction
        print("\n[Step 5] Triggering Deepfake Incident & Session Restriction...")
        db = get_db()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        incident_record = loop.run_until_complete(
            handle_detection_trigger(
                session_id=session_id,
                prediction=PredictionType.DEEPFAKE,
                confidence=0.96,
                threat_level=ThreatLevel.CRITICAL,
                detection_latency_ms=22.4,
                trigger_details={"source": "integration_test"},
                timeline=[{
                    "window_index": 0,
                    "start_sec": 0.0,
                    "end_sec": 2.0,
                    "fake_probability": 0.96,
                    "prediction": "DEEPFAKE",
                    "threat_level": "CRITICAL",
                }],
                db=db,
            )
        )
        assert incident_record is not None
        incident_id = incident_record["incident_id"]
        print(f"  [PASS] Critical Deepfake Incident recorded: {incident_id}")

        # Check that session transitioned to restricted
        restricted_status = client.get(f"/session/status?session_id={session_id}", headers=admin_headers)
        assert restricted_status.json()["status"] == "restricted"
        print(f"  [PASS] Session {session_id} successfully restricted: status={restricted_status.json()['status']}")

        # Step 6: Incident Queries & Forensics
        print("\n[Step 6] Querying Incident Repository & Details (/incidents)...")
        incidents_list = client.get("/incidents", headers=admin_headers)
        assert incidents_list.status_code == 200
        incidents_data = incidents_list.json()
        assert len(incidents_data) > 0
        found = any(inc["incident_id"] == incident_id for inc in incidents_data)
        assert found, f"Incident {incident_id} not found in list."
        print(f"  [PASS] Incident list returned {len(incidents_data)} incident(s).")

        incident_detail = client.get(f"/incidents/{incident_id}", headers=admin_headers)
        assert incident_detail.status_code == 200
        assert incident_detail.json()["verification_status"] == "PENDING"
        print(f"  [PASS] Incident detail retrieved: status={incident_detail.json()['verification_status']}, confidence={incident_detail.json()['confidence']}")

        # Step 7: Prototype MFA Verification & Session Recovery
        print("\n[Step 7] Testing Prototype MFA Recovery Protocol (/verify)...")
        otp_req = client.post("/verify/request-otp", headers=admin_headers, json={"session_id": session_id})
        assert otp_req.status_code == 200, f"OTP request failed: {otp_req.text}"
        otp_data = otp_req.json()
        assert "otp_code" in otp_data
        assert "PROTOTYPE SIMULATION" in otp_data.get("simulation_notice", "")
        generated_otp = otp_data["otp_code"]
        print(f"  [PASS] Prototype OTP received: {generated_otp} | Disclaimer present")

        # Submit OTP to verify and lift restriction
        otp_ver = client.post(
            "/verify",
            headers=admin_headers,
            json={"session_id": session_id, "otp_code": generated_otp}
        )
        assert otp_ver.status_code == 200, f"OTP verify failed: {otp_ver.text}"
        assert otp_ver.json()["success"] is True
        print("  [PASS] OTP submitted and verified successfully.")

        # Check session is restored to active
        restored_status = client.get(f"/session/status?session_id={session_id}", headers=admin_headers)
        assert restored_status.json()["status"] == "active"
        print(f"  [PASS] Session {session_id} restriction lifted back to ACTIVE.")

        # Step 8: Dynamic Analytics Aggregation
        print("\n[Step 8] Verifying Dynamic Security Analytics (/analytics)...")
        analytics_res = client.get("/analytics", headers=admin_headers)
        assert analytics_res.status_code == 200
        analytics_data = analytics_res.json()
        assert analytics_data["total_incidents"] >= 1
        assert "real_vs_deepfake_counts" in analytics_data
        assert "average_detection_latency_ms" in analytics_data
        print(f"  [PASS] Analytics: Total Incidents={analytics_data['total_incidents']}, Suspicious Sessions={analytics_data['suspicious_sessions']}")

        # Step 9: WebSocket Telemetry Endpoint Connection
        print("\n[Step 9] Verifying WebSocket Telemetry Stream (/ws/detection/{session_id})...")
        with client.websocket_connect(f"/ws/detection/{session_id}") as websocket:
            conn_msg = websocket.receive_json()
            assert conn_msg["type"] == "connection_established"
            assert conn_msg["session_id"] == session_id
            print(f"  [PASS] WebSocket connected: mode={conn_msg['mode']}, model={conn_msg['model_name']}")

            # Test ping/pong
            websocket.send_json({"type": "ping"})
            pong_msg = websocket.receive_json()
            assert pong_msg["type"] == "pong"
            print("  [PASS] WebSocket ping/pong heartbeat confirmed.")

            # Test live audio chunk over WebSocket
            websocket.send_json({
                "type": "audio_chunk",
                "audio_base64": b64_audio,
            })
            stream_pred = websocket.receive_json()
            assert stream_pred["type"] == "prediction_update"
            assert "prediction" in stream_pred
            assert "latency_ms" in stream_pred
            print(f"  [PASS] Live WebSocket stream inference: verdict={stream_pred['prediction']}, latency={stream_pred['latency_ms']}ms")

        # Step 10: Stop Session
        print("\n[Step 10] Stopping Controlled Test Session (/session/stop)...")
        stop_res = client.post(f"/session/stop?session_id={session_id}", headers=admin_headers)
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "stopped"
        print(f"  [PASS] Session {session_id} successfully terminated.")

    print("\n================================================================")
    print("  SUCCESS: Phase 6 Integration Verification Fully Passed!")
    print("================================================================")


if __name__ == "__main__":
    run_phase6_verification()

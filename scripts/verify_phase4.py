"""
Phase 4 Verification Suite for SHADOW-NET.
Tests:
1. User registration & Session initiation (/session/start).
2. Automated Incident Response trigger upon high-confidence Deepfake detection.
3. Verification that session status transitions to 'restricted'.
4. Incident retrieval with date/threat filters and detection timeline (/incidents).
5. Dynamic analytics computation from MongoDB (/analytics).
6. Prototype MFA OTP generation and session recovery (/verify).
7. WebSocket live streaming connection (/ws/detection/{session_id}).
"""

import sys
import base64
import asyncio
from pathlib import Path
import soundfile as sf
import numpy as np

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient
from main import app
from app.db import get_db
from app.services.incident_service import handle_detection_trigger
from app.models.incident import PredictionType, ThreatLevel


def run_phase4_verification():
    print("================================================================")
    print("      SHADOW-NET Phase 4 Real-Time & Response Verification")
    print("================================================================")

    with TestClient(app) as client:
        # 1. Register & Authenticate Test Operator
        print("\n[Step 1] Authenticating Operator for Controlled Session...")
        user_creds = {
            "username": "phase4_operator",
            "email": "operator4@shadow.net",
            "password": "Phase4OperatorPassword!",
            "role": "Security Analyst",
        }
        res_reg = client.post("/auth/register", json=user_creds)
        assert res_reg.status_code in [201, 400]

        res_login = client.post("/auth/login", json={"username": "phase4_operator", "password": "Phase4OperatorPassword!"})
        assert res_login.status_code == 200, f"Login failed: {res_login.text}"
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [PASS] Operator authenticated, JWT token obtained.")

        # 2. Start Controlled Test Session
        print("\n[Step 2] Initiating Controlled Test Session (/session/start)...")
        session_res = client.post(
            "/session/start",
            headers=headers,
            json={"client_label": "Controlled Phase 4 Test Mic", "store_audio": False}
        )
        assert session_res.status_code == 201, f"Session start failed: {session_res.text}"
        session_id = session_res.json()["session_id"]
        assert session_res.json()["status"] == "active"
        print(f"  [PASS] Session initiated: {session_id} | Status: active")

        # 3. Trigger High-Confidence Deepfake Incident Response
        print("\n[Step 3] Simulating High-Confidence Deepfake Incident Trigger...")
        db = get_db()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Trigger detection incident
        incident_doc = loop.run_until_complete(
            handle_detection_trigger(
                session_id=session_id,
                prediction=PredictionType.DEEPFAKE,
                confidence=0.96,
                threat_level=ThreatLevel.CRITICAL,
                detection_latency_ms=18.5,
                trigger_details={"source": "simulated_deepfake_stream", "synthetic_score": 0.96},
                timeline=[
                    {"window_index": 0, "fake_probability": 0.35, "prediction": "REAL"},
                    {"window_index": 1, "fake_probability": 0.96, "prediction": "DEEPFAKE"},
                ],
                db=db,
            )
        )
        assert incident_doc is not None, "Incident document must be created"
        incident_id = incident_doc["incident_id"]
        print(f"  [PASS] Incident created: ID={incident_id} | Threat=CRITICAL | Action=RESTRICT_SESSION")

        # Verify session state was restricted
        session_check = client.get(f"/session/status?session_id={session_id}", headers=headers)
        assert session_check.status_code == 200
        assert session_check.json()["status"] == "restricted", f"Expected 'restricted', got {session_check.json()['status']}"
        print(f"  [PASS] Verified session {session_id} moved to 'restricted' status.")

        # 4. Verify Incidents API & Detection Timeline
        print("\n[Step 4] Querying Incidents API (/incidents)...")
        res_incidents = client.get(f"/incidents?session_id={session_id}&threat_level=CRITICAL", headers=headers)
        assert res_incidents.status_code == 200
        incidents_list = res_incidents.json()
        assert len(incidents_list) >= 1
        assert incidents_list[0]["incident_id"] == incident_id
        print(f"  [PASS] Filtered incidents query returned {len(incidents_list)} matching record(s).")

        # Query incident details + timeline
        res_detail = client.get(f"/incidents/{incident_id}", headers=headers)
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["incident_id"] == incident_id
        assert len(detail_data["timeline"]) == 2
        print(f"  [PASS] Incident detail retrieved with {len(detail_data['timeline'])} timeline window events.")

        # 5. Verify Dynamic Analytics API
        print("\n[Step 5] Checking Dynamic Analytics (/analytics)...")
        res_analytics = client.get("/analytics", headers=headers)
        assert res_analytics.status_code == 200
        analytics = res_analytics.json()
        print(f"  [PASS] Total Incidents: {analytics['total_incidents']}")
        print(f"  [PASS] Suspicious Sessions: {analytics['suspicious_sessions']}")
        print(f"  [PASS] Real vs. Deepfake: {analytics['real_vs_deepfake_counts']}")
        print(f"  [PASS] Average Confidence: {analytics['average_confidence']}")
        print(f"  [PASS] Threat Distribution: {analytics['threat_level_distribution']}")
        assert analytics["total_incidents"] >= 1
        assert analytics["suspicious_sessions"] >= 1

        # 6. Verify Prototype MFA Recovery Flow
        print("\n[Step 6] Testing Prototype MFA Verification & Session Recovery (/verify)...")
        # Request OTP
        res_otp = client.post("/verify/request-otp", headers=headers, json={"session_id": session_id})
        assert res_otp.status_code == 200, f"OTP request failed: {res_otp.text}"
        otp_data = res_otp.json()
        otp_code = otp_data["otp_code"]
        assert "PROTOTYPE SIMULATION" in otp_data["simulation_notice"]
        print(f"  [PASS] Received prototype MFA OTP: {otp_code} (Simulation notice present)")

        # Verify invalid code rejection
        res_bad = client.post("/verify", headers=headers, json={"session_id": session_id, "otp_code": "000000"})
        assert res_bad.status_code == 400
        print("  [PASS] Invalid OTP correctly rejected with 400 Bad Request.")

        # Submit valid OTP
        res_verify = client.post("/verify", headers=headers, json={"session_id": session_id, "otp_code": otp_code})
        assert res_verify.status_code == 200, f"Verification failed: {res_verify.text}"
        verify_data = res_verify.json()
        assert verify_data["success"] is True
        assert verify_data["status"] == "active"
        print("  [PASS] Valid OTP verified. Session restriction lifted!")

        # Confirm session status is now active again
        res_final_session = client.get(f"/session/status?session_id={session_id}", headers=headers)
        assert res_final_session.json()["status"] == "active"
        print("  [PASS] Session status confirmed: 'active'.")

        # Confirm incident verification status updated to VERIFIED
        res_final_incident = client.get(f"/incidents/{incident_id}", headers=headers)
        assert res_final_incident.json()["verification_status"] == "VERIFIED"
        print("  [PASS] Incident verification status confirmed: 'VERIFIED'.")

        # 7. Verify WebSocket Live Streaming Connection
        print("\n[Step 7] Testing WebSocket Connection (/ws/detection/{session_id})...")
        with client.websocket_connect(f"/ws/detection/{session_id}") as ws:
            # First frame should be connection_established
            hello_msg = ws.receive_json()
            assert hello_msg["type"] == "connection_established"
            assert hello_msg["session_id"] == session_id
            print(f"  [PASS] WebSocket connected successfully: Type={hello_msg['type']} | Mode={hello_msg['mode']}")

            # Send ping
            ws.send_json({"type": "ping"})
            pong_msg = ws.receive_json()
            assert pong_msg["type"] == "pong"
            print("  [PASS] WebSocket ping/pong verified.")

    print("\n================================================================")
    print("  ALL PHASE 4 REAL-TIME & RESPONSE CHECKS PASSED! (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_phase4_verification()

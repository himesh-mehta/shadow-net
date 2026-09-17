"""
Phase 1 Verification Script for SHADOW-NET
Tests:
1. User registration across roles (Administrator, Security Analyst, User)
2. Login and JWT issuance
3. Protected route access (/auth/me)
4. Role-based access control (/settings admin-only gating)
5. Session start, status inspection, stop, and persistence
"""

import asyncio
import sys
from pathlib import Path

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


def run_phase1_verification():
    print("================================================================")
    print("      SHADOW-NET Phase 1 Backend Verification Suite")
    print("================================================================")

    # Initialize client (with lifespan event handlers)
    with TestClient(app) as client:
        # 1. Health check
        print("\n[Step 1] Checking /health endpoint...")
        res = client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        health_data = res.json()
        print(f"  [PASS] Service status: {health_data.get('status')}")
        print(f"  [PASS] Database status: {health_data.get('database')}")

        # 2. User Registration
        print("\n[Step 2] Testing User Registration...")
        admin_data = {
            "username": "admin_agent",
            "email": "admin@shadow.net",
            "password": "SuperSecureAdminPassword123!",
            "role": "Administrator",
        }
        res = client.post("/auth/register", json=admin_data)
        assert res.status_code == 201, f"Admin registration failed: {res.text}"
        admin_info = res.json()
        print(f"  [PASS] Registered Administrator: {admin_info['username']} (ID: {admin_info['id']})")

        analyst_data = {
            "username": "analyst_sec",
            "email": "analyst@shadow.net",
            "password": "AnalystPassword456!",
            "role": "Security Analyst",
        }
        res = client.post("/auth/register", json=analyst_data)
        assert res.status_code == 201, f"Analyst registration failed: {res.text}"
        print(f"  [PASS] Registered Security Analyst: {res.json()['username']}")

        user_data = {
            "username": "test_operator",
            "email": "operator@shadow.net",
            "password": "OperatorPassword789!",
            "role": "User",
        }
        res = client.post("/auth/register", json=user_data)
        assert res.status_code == 201, f"User registration failed: {res.text}"
        user_info = res.json()
        print(f"  [PASS] Registered Standard User: {user_info['username']} (ID: {user_info['id']})")

        # Duplicate registration test
        res = client.post("/auth/register", json=admin_data)
        assert res.status_code == 400, "Duplicate registration should return 400"
        print("  [PASS] Duplicate registration correctly rejected with 400")

        # 3. Login & JWT Issuance
        print("\n[Step 3] Testing Login & JWT Issuance...")
        # Admin Login
        res = client.post("/auth/login", json={"username": "admin_agent", "password": "SuperSecureAdminPassword123!"})
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        admin_token = res.json()["access_token"]
        print("  [PASS] Admin login succeeded, JWT issued")

        # Standard User Login
        res = client.post("/auth/login", json={"username": "test_operator", "password": "OperatorPassword789!"})
        assert res.status_code == 200, f"User login failed: {res.text}"
        user_token = res.json()["access_token"]
        print("  [PASS] User login succeeded, JWT issued")

        # Invalid password test
        res = client.post("/auth/login", json={"username": "test_operator", "password": "WrongPassword!"})
        assert res.status_code == 401, "Invalid password should return 401"
        print("  [PASS] Invalid password rejected with 401 Unauthorized")

        # 4. Protected Route & User Profile (/auth/me)
        print("\n[Step 4] Testing Protected Route (/auth/me)...")
        headers_user = {"Authorization": f"Bearer {user_token}"}
        res = client.get("/auth/me", headers=headers_user)
        assert res.status_code == 200, f"GET /auth/me failed: {res.text}"
        profile = res.json()
        assert profile["username"] == "test_operator"
        assert profile["role"] == "User"
        print(f"  [PASS] Verified profile for: {profile['username']} | Role: {profile['role']}")

        # Unauthenticated request
        res = client.get("/auth/me")
        assert res.status_code in [401, 403], f"Unauthenticated request should return 401/403, got {res.status_code}"
        print("  [PASS] Unauthenticated access correctly blocked")

        # 5. Role-Based Access Control (/settings)
        print("\n[Step 5] Testing RBAC on Admin-Only Settings...")
        # Standard user attempt
        res = client.put("/settings", headers=headers_user, json={"detection_threshold": 0.85})
        assert res.status_code == 403, f"Standard user should get 403 Forbidden, got {res.status_code}"
        print("  [PASS] Standard user blocked from updating settings (403 Forbidden)")

        # Admin user attempt
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        res = client.put(
            "/settings",
            headers=headers_admin,
            json={"detection_threshold": 0.82, "audio_window_length": 1.5, "demo_mode": True}
        )
        assert res.status_code == 200, f"Admin settings update failed: {res.text}"
        updated_settings = res.json()
        assert updated_settings["detection_threshold"] == 0.82
        assert updated_settings["audio_window_length"] == 1.5
        print(f"  [PASS] Admin updated settings: Threshold={updated_settings['detection_threshold']}, Window={updated_settings['audio_window_length']}s")

        # 6. Session Lifecycle & Persistence
        print("\n[Step 6] Testing Controlled Session Management & DB Persistence...")
        session_payload = {
            "client_label": "Test Bench Controlled Audio Mic 01",
            "store_audio": False,  # Default privacy setting
            "notes": "Controlled Phase 1 test session verification",
        }
        res = client.post("/session/start", headers=headers_user, json=session_payload)
        assert res.status_code == 201, f"Session start failed: {res.text}"
        session_data = res.json()
        session_id = session_data["session_id"]
        assert session_data["status"] == "active"
        assert session_data["store_audio"] is False
        print(f"  [PASS] Session started: ID={session_id} | Status={session_data['status']}")
        print(f"  [PASS] Privacy check: store_audio={session_data['store_audio']}")

        # Inspect status
        res = client.get(f"/session/status?session_id={session_id}", headers=headers_user)
        assert res.status_code == 200, f"Get session status failed: {res.text}"
        assert res.json()["status"] == "active"
        print("  [PASS] Session status verified: active")

        # Stop session
        res = client.post(f"/session/stop?session_id={session_id}", headers=headers_user)
        assert res.status_code == 200, f"Stop session failed: {res.text}"
        stopped_session = res.json()
        assert stopped_session["status"] == "stopped"
        assert stopped_session["stopped_at"] is not None
        print(f"  [PASS] Session stopped: ID={session_id} | StoppedAt={stopped_session['stopped_at']}")

        # Verify DB persistence directly
        db = get_db()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        saved_doc = loop.run_until_complete(db.sessions.find_one({"session_id": session_id}))
        assert saved_doc is not None, "Session document must exist in MongoDB"
        assert saved_doc["status"] == "stopped"
        assert saved_doc["store_audio"] is False
        print(f"  [PASS] Verified MongoDB persistence: Document ID={saved_doc['_id']} | Status={saved_doc['status']}")

    print("\n================================================================")
    print("  ALL PHASE 1 VERIFICATION TESTS PASSED SUCCESSFULLY! (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_phase1_verification()

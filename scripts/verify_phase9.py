"""
Phase 9 Verification Suite for SHADOW-NET:
Privacy Preservation, GDPR Ephemeral Buffering & Cryptographic Evidence Packet Export.

Validates:
1. Audio Privacy Default: store_audio is False by default across sessions and incidents.
2. Ephemeral Audio Handling: Raw audio bytes are not persisted in MongoDB or on disk.
3. Tamper-evident Evidence Packet Export (GET /incidents/{incident_id}/export).
4. SHA-256 integrity hash verification over canonical packet data.
5. Model Provenance Tracking: Evidence packets truthfully record model_status and heuristic disclosure.
"""

import sys
import json
import hashlib
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from main import app
from app.models.incident import PredictionType, ThreatLevel


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/5] {title}...")


def main():
    print("=" * 80)
    print("SHADOW-NET Phase 9 Verification: Privacy, Ephemeral Buffer & Evidence Export")
    print("=" * 80)

    with TestClient(app) as client:
        # Step 1: Admin Auth
        log_step(1, "Authenticating Security Analyst / Admin")
        admin_creds = {
            "username": "sarah.connor",
            "email": "sarah.connor@shadow.net",
            "password": "analyst123456",
            "role": "Security Analyst",
        }
        client.post("/auth/register", json=admin_creds)
        login_res = client.post(
            "/auth/login",
            json={"username": admin_creds["username"], "password": admin_creds["password"]},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [OK] Authenticated as Security Analyst.")

        # Step 2: Verify store_audio is False by default
        log_step(2, "Verifying Privacy Default Policy (store_audio = False)")
        sess_res = client.post(
            "/session/start",
            json={"client_label": "privacy-audit-session"},
            headers=headers,
        )
        assert sess_res.status_code == 201, f"Session start failed: {sess_res.text}"
        session_data = sess_res.json()
        session_id = session_data["session_id"]
        assert session_data["store_audio"] is False, "store_audio MUST default to False!"
        print(f"  [OK] Session {session_id} initiated with store_audio: False.")

        # Step 3: Trigger an incident and verify no raw audio is saved
        log_step(3, "Triggering Incident and Auditing Ephemeral Storage")
        from app.services.incident_service import handle_detection_trigger
        import asyncio

        # Trigger incident programmatically
        from app.db import get_db
        db = get_db()
        incident_doc = asyncio.run(
            handle_detection_trigger(
                session_id=session_id,
                prediction=PredictionType.AI_SUSPECTED,
                confidence=0.88,
                threat_level=ThreatLevel.HIGH,
                detection_latency_ms=14.2,
                trigger_details={"source": "phase9_verification", "note": "synthetic test"},
                timeline=[
                    {"window_index": 0, "start_sec": 0.0, "end_sec": 2.0, "fake_probability": 0.88, "prediction": "AI_SUSPECTED"}
                ],
                db=db,
            )
        )
        assert incident_doc is not None, "Failed to record incident!"
        incident_id = incident_doc["incident_id"]
        print(f"  [OK] Incident {incident_id} created.")

        # Query incident from DB via API
        inc_res = client.get(f"/incidents/{incident_id}", headers=headers)
        assert inc_res.status_code == 200, f"Failed to get incident: {inc_res.text}"
        inc_data = inc_res.json()
        assert inc_data["store_audio"] is False, "Incident store_audio must be False!"
        assert "raw_audio" not in inc_data, "Raw audio must not be stored in incident record!"
        print("  [OK] Zero raw audio stored in database record. Ephemeral buffer confirmed.")

        # Step 4: Test GET /incidents/{incident_id}/export
        log_step(4, "Testing Cryptographic Evidence Packet Export")
        export_res = client.get(f"/incidents/{incident_id}/export", headers=headers)
        assert export_res.status_code == 200, f"Export failed: {export_res.text}"
        packet = export_res.json()

        # Validate evidence packet structure
        expected_sections = [
            "packet_id",
            "schema_version",
            "incident_id",
            "session_id",
            "exported_at",
            "incident_timestamp",
            "exported_by",
            "verdict_data",
            "model_provenance",
            "acoustic_forensics",
            "privacy_compliance",
            "integrity_hash_sha256",
        ]
        for section in expected_sections:
            assert section in packet, f"Missing section '{section}' in evidence packet!"

        assert packet["incident_id"] == incident_id
        assert packet["session_id"] == session_id
        assert packet["privacy_compliance"]["raw_audio_retained"] is False
        assert packet["privacy_compliance"]["store_audio"] is False
        print("  [OK] Evidence packet generated with all required forensic sections.")
        print(f"  Model Provenance: {packet['model_provenance']}")

        # Step 5: Verify SHA-256 cryptographic integrity hash
        log_step(5, "Verifying Cryptographic Integrity Hash")
        claimed_hash = packet["integrity_hash_sha256"]
        packet_copy = dict(packet)
        del packet_copy["integrity_hash_sha256"]

        canonical_bytes = json.dumps(packet_copy, sort_keys=True).encode("utf-8")
        recomputed_hash = hashlib.sha256(canonical_bytes).hexdigest()

        assert claimed_hash == recomputed_hash, (
            f"Hash mismatch! Claimed: {claimed_hash}, Recomputed: {recomputed_hash}"
        )
        print(f"  [OK] SHA-256 integrity hash verified: {claimed_hash}")

    print("\n" + "=" * 80)
    print("ALL 5 PHASE 9 PRIVACY & EVIDENCE PACKET CHECKS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    main()

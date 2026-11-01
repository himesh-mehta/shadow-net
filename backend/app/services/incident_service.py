"""
Incident Response and MFA Verification Service for SHADOW-NET.
Handles:
1. Automated incident logging when synthetic deepfakes are detected
2. Session restriction triggers
3. WebSocket alert broadcasting
4. Prototype MFA OTP generation and verification

DISCLAIMER & PROTOTYPE NOTICE:
The MFA verification mechanism here is a prototype simulation for demonstration
purposes and does not integrate live telecom/SMS carrier networks.
"""

import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.models.incident import PredictionType, ThreatLevel, ResponseAction, VerificationStatus
from app.models.session import SessionStatus
from app.services.ws_manager import ws_manager

logger = logging.getLogger("shadow_net.incident_service")

PROTOTYPE_MFA_DISCLAIMER = (
    "PROTOTYPE SIMULATION ONLY: This MFA flow is an experimental security demonstration "
    "operating within a controlled test bench. It does not perform live SMS or telephony verification."
)


async def handle_detection_trigger(
    session_id: str,
    prediction: PredictionType,
    confidence: float,
    threat_level: ThreatLevel,
    detection_latency_ms: float,
    trigger_details: Optional[Dict[str, Any]] = None,
    timeline: Optional[list] = None,
    db=None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates detection results. If deepfake threshold is exceeded:
    1. Inserts Incident document into MongoDB
    2. Moves session status to 'restricted'
    3. Broadcasts WebSocket alert event to frontend
    """
    if prediction not in [PredictionType.DEEPFAKE, PredictionType.AI_SUSPECTED] or db is None:
        return None

    incident_id = str(uuid.uuid4())
    now = datetime.utcnow()
    action = ResponseAction.RESTRICT_SESSION if threat_level == ThreatLevel.CRITICAL else ResponseAction.ALERT

    incident_doc = {
        "incident_id": incident_id,
        "session_id": session_id,
        "timestamp": now,
        "prediction": prediction.value,
        "confidence": confidence,
        "threat_level": threat_level.value,
        "detection_latency": detection_latency_ms,
        "response_action": action.value,
        "verification_status": VerificationStatus.PENDING.value,
        "trigger_details": trigger_details or {},
        "timeline": timeline or [],
        "store_audio": False,
    }

    # 1. Persist incident in MongoDB
    await db.incidents.insert_one(incident_doc)
    logger.warning(f"Recorded incident {incident_id} for session {session_id} (Threat: {threat_level.value}, Action: {action.value})")

    # 2. Restrict session in MongoDB if actionable threat
    if action == ResponseAction.RESTRICT_SESSION:
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": SessionStatus.RESTRICTED.value, "restricted_at": now}}
        )
        logger.warning(f"Session {session_id} state set to 'restricted'. Identity verification required.")

    # 3. Push real-time alert event over WebSocket
    alert_packet = {
        "type": "alert",
        "incident_id": incident_id,
        "session_id": session_id,
        "timestamp": now.isoformat(),
        "prediction": prediction.value,
        "confidence": confidence,
        "threat_level": threat_level.value,
        "response_action": action.value,
        "message": f"Suspected AI speech: model score {confidence*100:.1f}%. Prototype response: {action.value}.",
        "requires_verification": (action == ResponseAction.RESTRICT_SESSION),
    }
    await ws_manager.broadcast_to_session(session_id, alert_packet)

    return incident_doc


async def request_mfa_otp(session_id: str, user_id: str, db) -> Dict[str, Any]:
    """
    Generates a 6-digit prototype MFA OTP for a restricted session.
    Returns OTP in dev response with explicit prototype simulation warning.
    """
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        raise ValueError(f"Session '{session_id}' not found.")

    otp = f"{random.randint(100000, 999999)}"
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=10)

    verification_doc = {
        "verification_id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "otp_code": otp,
        "created_at": now,
        "expires_at": expires_at,
        "is_used": False,
        "simulation_disclaimer": PROTOTYPE_MFA_DISCLAIMER,
    }

    # Store or replace active verification
    await db.verifications.update_one(
        {"session_id": session_id},
        {"$set": verification_doc},
        upsert=True,
    )

    logger.info(f"[PROTOTYPE MFA] Generated OTP for session {session_id}: {otp}")

    return {
        "session_id": session_id,
        "otp_code": otp,  # Exposed for developer testing
        "expires_in_seconds": 600,
        "simulation_notice": PROTOTYPE_MFA_DISCLAIMER,
        "message": "Prototype MFA code generated. In real production, this would be delivered via Out-Of-Band telephony.",
    }


async def verify_mfa_otp(session_id: str, otp_code: str, db) -> Dict[str, Any]:
    """
    Verifies submitted OTP code. If valid, lifts session restriction back to 'active'
    and updates any pending incidents for this session to 'VERIFIED'.
    """
    verif = await db.verifications.find_one({
        "session_id": session_id,
        "otp_code": otp_code.strip(),
        "is_used": False,
    })

    if not verif:
        return {"success": False, "detail": "Invalid or expired verification code."}

    if datetime.utcnow() > verif["expires_at"]:
        return {"success": False, "detail": "Verification code has expired."}

    # Mark OTP as used
    await db.verifications.update_one(
        {"_id": verif["_id"]},
        {"$set": {"is_used": True, "verified_at": datetime.utcnow()}}
    )

    # Restore session state to active
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": SessionStatus.ACTIVE.value, "unlocked_at": datetime.utcnow()}}
    )

    # Update associated incidents to VERIFIED
    await db.incidents.update_many(
        {"session_id": session_id, "verification_status": VerificationStatus.PENDING.value},
        {"$set": {"verification_status": VerificationStatus.VERIFIED.value}}
    )

    # Broadcast unlock packet over WebSocket
    unlock_packet = {
        "type": "session_resumed",
        "session_id": session_id,
        "status": "active",
        "message": "Identity verified via prototype MFA. Session restrictions lifted.",
        "timestamp": datetime.utcnow().isoformat(),
    }
    await ws_manager.broadcast_to_session(session_id, unlock_packet)

    return {
        "success": True,
        "session_id": session_id,
        "status": "active",
        "simulation_notice": PROTOTYPE_MFA_DISCLAIMER,
        "message": "Verification successful. Session resumed.",
    }

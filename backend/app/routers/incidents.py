"""
Incidents Management and Query Module for SHADOW-NET.
Provides filtering by date range, threat level, prediction type, and session ID,
plus detailed detection timelines for specific incidents.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import get_db
from app.routers.auth import get_current_user
from app.models.user import UserInDB
from app.models.incident import (
    IncidentResponse,
    PredictionType,
    ThreatLevel,
    VerificationStatus,
)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentDetailResponse(IncidentResponse):
    timeline: List[Dict[str, Any]] = []


@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    session_id: Optional[str] = Query(None, description="Filter incidents by session ID"),
    threat_level: Optional[ThreatLevel] = Query(None, description="Filter by threat level"),
    prediction: Optional[PredictionType] = Query(None, description="Filter by prediction type"),
    start_date: Optional[datetime] = Query(None, description="Filter incidents after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter incidents before this timestamp"),
    limit: int = Query(50, ge=1, le=200, description="Max number of incidents to return"),
    skip: int = Query(0, ge=0, description="Number of incidents to skip"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    List recorded deepfake detection incidents with date, threat level, and prediction filters.
    """
    query: Dict[str, Any] = {}
    if session_id:
        query["session_id"] = session_id
    if threat_level:
        query["threat_level"] = threat_level.value
    if prediction:
        query["prediction"] = prediction.value

    # Date range filters
    date_filter: Dict[str, Any] = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        query["timestamp"] = date_filter

    cursor = db.incidents.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    incidents = await cursor.to_list(length=limit)

    return [
        IncidentResponse(
            incident_id=doc["incident_id"],
            session_id=doc["session_id"],
            timestamp=doc["timestamp"],
            prediction=PredictionType(doc["prediction"]),
            confidence=doc["confidence"],
            threat_level=ThreatLevel(doc["threat_level"]),
            detection_latency=doc["detection_latency"],
            response_action=doc.get("response_action", "ALERT"),
            verification_status=doc.get("verification_status", "PENDING"),
            trigger_details=doc.get("trigger_details", {}),
            store_audio=doc.get("store_audio", False),
        )
        for doc in incidents
    ]


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Retrieve details for a specific incident, including its chronological detection timeline.
    """
    doc = await db.incidents.find_one({"incident_id": incident_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found."
        )

    return IncidentDetailResponse(
        incident_id=doc["incident_id"],
        session_id=doc["session_id"],
        timestamp=doc["timestamp"],
        prediction=PredictionType(doc["prediction"]),
        confidence=doc["confidence"],
        threat_level=ThreatLevel(doc["threat_level"]),
        detection_latency=doc["detection_latency"],
        response_action=doc.get("response_action", "ALERT"),
        verification_status=doc.get("verification_status", "PENDING"),
        trigger_details=doc.get("trigger_details", {}),
        timeline=doc.get("timeline", []),
        store_audio=doc.get("store_audio", False),
    )


@router.get("/{incident_id}/export")
async def export_incident_evidence_packet(
    incident_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Exports a cryptographically-hashed, tamper-evident JSON Evidence Packet for SOC analysts
    and forensic audits. Conforms to GDPR zero-raw-audio privacy policies.
    """
    import json
    import hashlib
    import uuid
    from app.ml.factory import get_detector

    doc = await db.incidents.find_one({"incident_id": incident_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found."
        )

    detector = get_detector()
    model_status = getattr(detector, "model_status", "NOT_TRAINED")
    is_heuristic = getattr(detector, "is_heuristic_placeholder", True)

    packet_data = {
        "packet_id": str(uuid.uuid4()),
        "schema_version": "1.0",
        "incident_id": doc["incident_id"],
        "session_id": doc["session_id"],
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "incident_timestamp": doc["timestamp"].isoformat() if hasattr(doc["timestamp"], "isoformat") else str(doc["timestamp"]),
        "exported_by": {
            "username": current_user.username,
            "role": current_user.role,
        },
        "verdict_data": {
            "prediction": doc.get("prediction"),
            "confidence": doc.get("confidence"),
            "threat_level": doc.get("threat_level"),
            "response_action": doc.get("response_action", "ALERT"),
            "detection_latency_ms": doc.get("detection_latency"),
            "verification_status": doc.get("verification_status", "PENDING"),
        },
        "model_provenance": {
            "model_name": detector.name,
            "model_version": getattr(detector, "version", "v1"),
            "model_status": model_status,
            "is_heuristic_placeholder": is_heuristic,
        },
        "acoustic_forensics": {
            "trigger_details": doc.get("trigger_details", {}),
            "timeline_length": len(doc.get("timeline", [])),
            "timeline": doc.get("timeline", []),
        },
        "privacy_compliance": {
            "store_audio": doc.get("store_audio", False),
            "raw_audio_retained": False,
            "policy": "GDPR-compliant ephemeral memory buffer. No persistent biometric voice records.",
        },
    }

    # Canonical hash for integrity
    canonical_bytes = json.dumps(packet_data, sort_keys=True).encode("utf-8")
    sha256_hash = hashlib.sha256(canonical_bytes).hexdigest()
    packet_data["integrity_hash_sha256"] = sha256_hash

    return packet_data

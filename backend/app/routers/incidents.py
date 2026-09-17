"""
Incidents management and query module for SHADOW-NET.
Provides visibility into logged deepfake detection events and threat mitigation actions.
"""

from typing import Optional, List
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


@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    session_id: Optional[str] = Query(None, description="Filter incidents by session ID"),
    threat_level: Optional[ThreatLevel] = Query(None, description="Filter by threat level"),
    prediction: Optional[PredictionType] = Query(None, description="Filter by prediction type"),
    limit: int = Query(50, ge=1, le=200, description="Max number of incidents to return"),
    skip: int = Query(0, ge=0, description="Number of incidents to skip"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    List recorded deepfake detection incidents with optional filters.
    """
    query = {}
    if session_id:
        query["session_id"] = session_id
    if threat_level:
        query["threat_level"] = threat_level.value
    if prediction:
        query["prediction"] = prediction.value

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


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Retrieve details for a specific incident by its unique identifier.
    """
    doc = await db.incidents.find_one({"incident_id": incident_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found."
        )

    return IncidentResponse(
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

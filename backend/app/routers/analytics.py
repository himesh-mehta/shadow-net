"""
Security Analytics Router for SHADOW-NET.
Provides aggregate metrics dynamically computed from MongoDB:
- Total incident count
- Suspicious sessions count
- Real vs. Deepfake vs. Uncertain distribution
- Average detection latency
- Average confidence score
- Threat level distribution
"""

from typing import Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends

from app.db import get_db
from app.routers.auth import get_current_user
from app.models.user import UserInDB

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class AnalyticsResponse(BaseModel):
    total_incidents: int
    suspicious_sessions: int
    real_vs_deepfake_counts: Dict[str, int]
    average_confidence: float
    average_detection_latency_ms: float
    threat_level_distribution: Dict[str, int]
    pending_verifications: int
    total_controlled_sessions: int


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Compute aggregate security metrics across all controlled test sessions and incidents.
    Aggregated dynamically from MongoDB collections (not hard-coded).
    """
    # 1. Total incidents count
    total_incidents = await db.incidents.count_documents({})

    # 2. Total controlled sessions count
    total_sessions = await db.sessions.count_documents({})

    # 3. Suspicious sessions: count sessions with status 'restricted' or having any deepfake incident
    suspicious_sessions = await db.sessions.count_documents({
        "$or": [
            {"status": "restricted"},
            {"status": "restricted_pending_mfa"}
        ]
    })
    # Also find unique sessions from incidents
    distinct_incident_sessions = await db.incidents.distinct("session_id", {"prediction": "DEEPFAKE"})
    # Union of restricted count and distinct incident sessions
    suspicious_sessions_count = max(suspicious_sessions, len(distinct_incident_sessions))

    # 4. Aggregate metrics across incidents
    real_count = await db.incidents.count_documents({"prediction": "REAL"})
    fake_count = await db.incidents.count_documents({"prediction": "DEEPFAKE"})
    uncertain_count = await db.incidents.count_documents({"prediction": "UNCERTAIN"})

    threat_distribution = {
        "LOW": await db.incidents.count_documents({"threat_level": "LOW"}),
        "MEDIUM": await db.incidents.count_documents({"threat_level": "MEDIUM"}),
        "HIGH": await db.incidents.count_documents({"threat_level": "HIGH"}),
        "CRITICAL": await db.incidents.count_documents({"threat_level": "CRITICAL"}),
    }

    pending_verifications = await db.incidents.count_documents({"verification_status": "PENDING"})

    # Compute averages via aggregation pipeline or cursor
    incidents_cursor = db.incidents.find({})
    all_incidents = await incidents_cursor.to_list(length=1000)

    if all_incidents:
        avg_conf = sum(doc.get("confidence", 0.0) for doc in all_incidents) / len(all_incidents)
        avg_lat = sum(doc.get("detection_latency", 0.0) for doc in all_incidents) / len(all_incidents)
    else:
        avg_conf = 0.0
        avg_lat = 0.0

    return AnalyticsResponse(
        total_incidents=total_incidents,
        suspicious_sessions=suspicious_sessions_count,
        real_vs_deepfake_counts={
            "REAL": real_count,
            "DEEPFAKE": fake_count,
            "UNCERTAIN": uncertain_count,
        },
        average_confidence=round(avg_conf, 4),
        average_detection_latency_ms=round(avg_lat, 2),
        threat_level_distribution=threat_distribution,
        pending_verifications=pending_verifications,
        total_controlled_sessions=total_sessions,
    )

"""
================================================================================
SHADOW-NET Session Management Module
================================================================================
CONTROLLED TEST ENVIRONMENT SPECIFICATION:
A "session" in SHADOW-NET is strictly a controlled test call or audio recording session
initiated by the user locally within a self-owned test environment (e.g., local
microphone input or designated test WAV file ingestion).

SHADOW-NET DOES NOT intercept, eavesdrop on, or tap into real third-party VoIP,
Zoom, Microsoft Teams, WebRTC, or carrier telephony infrastructure.
All detection analysis and responses operate solely on user-provided local test streams.

AUDIO PRIVACY NOTICE:
Raw voice recordings are NOT stored unless an explicit "store_audio=True" flag is
set by the user during session initialization. Default is strictly False.
================================================================================
"""

import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import get_db
from app.routers.auth import get_current_user
from app.models.user import UserInDB
from app.models.session import (
    SessionStatus,
    SessionCreate,
    SessionResponse,
    SessionInDB,
)

router = APIRouter(prefix="/session", tags=["Sessions"])


@router.get("/timeline", response_model=List[dict])
async def get_session_timeline(
    session_id: str = Query(..., description="Session ID to fetch analysis timeline for"),
    limit: int = Query(default=100, ge=1, le=500, description="Max events to return"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Returns the ordered analysis history for a session:
    verdict, confidence, fake_probability, threat level, latency, and timestamp
    for every audio analysis run against this session.

    Newest events are returned first. Only the session owner or an Administrator
    can access the timeline.
    """
    session_doc = await db.sessions.find_one({"session_id": session_id})
    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    if session_doc["user_id"] != current_user.id and current_user.role.value != "Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this session's timeline.",
        )

    cursor = db.analysis_timeline.find(
        {"session_id": session_id},
        {"_id": 0},
    ).sort("timestamp", -1).limit(limit)

    events = []
    async for doc in cursor:
        # Serialize datetime to ISO string for JSON
        if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
            doc["timestamp"] = doc["timestamp"].isoformat() + "Z"
        events.append(doc)

    return events



@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: SessionCreate = SessionCreate(),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Initiate a controlled test call/recording session for the current user.
    Creates an active session record in MongoDB.
    """
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    session_record = {
        "session_id": session_id,
        "user_id": current_user.id,
        "status": SessionStatus.ACTIVE.value,
        "client_label": payload.client_label or "Local Test Audio Client",
        "store_audio": payload.store_audio,  # Kept False by default
        "started_at": now,
        "stopped_at": None,
        "notes": payload.notes,
        "metadata": {
            "created_by": current_user.username,
            "role": current_user.role.value,
        },
    }

    await db.sessions.insert_one(session_record)

    return SessionResponse(
        session_id=session_id,
        user_id=current_user.id,
        status=SessionStatus.ACTIVE,
        client_label=session_record["client_label"],
        store_audio=payload.store_audio,
        started_at=now,
        stopped_at=None,
        notes=payload.notes,
    )


@router.post("/stop", response_model=SessionResponse)
async def stop_session(
    session_id: str = Query(..., description="ID of the session to terminate"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Stop an active controlled test session and update its status to 'stopped'.
    """
    session_doc = await db.sessions.find_one({"session_id": session_id})
    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    # Allow administrators to stop any session, otherwise only session owner
    if session_doc["user_id"] != current_user.id and current_user.role.value != "Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to stop this session."
        )

    if session_doc["status"] == SessionStatus.STOPPED.value:
        return SessionResponse(
            session_id=session_doc["session_id"],
            user_id=session_doc["user_id"],
            status=SessionStatus.STOPPED,
            client_label=session_doc.get("client_label", "Local Test Audio Client"),
            store_audio=session_doc.get("store_audio", False),
            started_at=session_doc["started_at"],
            stopped_at=session_doc.get("stopped_at"),
            notes=session_doc.get("notes"),
        )

    now = datetime.utcnow()
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": SessionStatus.STOPPED.value, "stopped_at": now}}
    )

    return SessionResponse(
        session_id=session_doc["session_id"],
        user_id=session_doc["user_id"],
        status=SessionStatus.STOPPED,
        client_label=session_doc.get("client_label", "Local Test Audio Client"),
        store_audio=session_doc.get("store_audio", False),
        started_at=session_doc["started_at"],
        stopped_at=now,
        notes=session_doc.get("notes"),
    )


@router.get("/status", response_model=SessionResponse)
async def get_session_status(
    session_id: Optional[str] = Query(None, description="Optional session ID. If omitted, returns current user's latest active session"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Retrieve the current status of a session.
    """
    if session_id:
        session_doc = await db.sessions.find_one({"session_id": session_id})
    else:
        # Find latest active session for current user
        session_doc = await db.sessions.find_one(
            {"user_id": current_user.id, "status": SessionStatus.ACTIVE.value},
            sort=[("started_at", -1)]
        )
        if not session_doc:
            # Fall back to latest session of any status
            session_doc = await db.sessions.find_one(
                {"user_id": current_user.id},
                sort=[("started_at", -1)]
            )

    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No session found."
        )

    return SessionResponse(
        session_id=session_doc["session_id"],
        user_id=session_doc["user_id"],
        status=SessionStatus(session_doc["status"]),
        client_label=session_doc.get("client_label", "Local Test Audio Client"),
        store_audio=session_doc.get("store_audio", False),
        started_at=session_doc["started_at"],
        stopped_at=session_doc.get("stopped_at"),
        notes=session_doc.get("notes"),
    )

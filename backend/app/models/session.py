"""
Session models and schemas for controlled test calls.

NOTICE:
A "session" in SHADOW-NET is strictly a controlled test call or audio recording session
run locally by the user within a self-owned test bench.
Raw audio recordings are NOT persisted unless an explicit "store_audio" flag is set.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    RESTRICTED = "restricted"
    COMPLETED = "completed"


class SessionCreate(BaseModel):
    client_label: Optional[str] = Field(default="Local Test Audio Client", description="Identifier for local audio source")
    store_audio: bool = Field(
        default=False,
        description="Explicit flag to store raw audio. Strictly False by default for privacy."
    )
    notes: Optional[str] = Field(default=None, description="Optional experiment or test session notes")


class SessionInDB(BaseModel):
    session_id: str
    user_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    client_label: str = "Local Test Audio Client"
    store_audio: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)
    stopped_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: SessionStatus
    client_label: str
    store_audio: bool
    started_at: datetime
    stopped_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

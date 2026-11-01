"""
Incident models and schemas for detected deepfake security events.

Fields per spec:
session id, timestamps, prediction, confidence, threat level, detection latency,
response action, verification status.
Audio is NOT stored unless explicit "store_audio" flag was authorized for the parent session.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PredictionType(str, Enum):
    REAL = "REAL"
    DEEPFAKE = "DEEPFAKE"
    AI_SUSPECTED = "AI_SUSPECTED"
    UNCERTAIN = "UNCERTAIN"


class ThreatLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResponseAction(str, Enum):
    ALERT = "ALERT"
    RESTRICT_SESSION = "RESTRICT_SESSION"
    REQUIRE_MFA = "REQUIRE_MFA"
    NONE = "NONE"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    BYPASSED = "BYPASSED"


class IncidentCreate(BaseModel):
    session_id: str
    prediction: PredictionType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    threat_level: ThreatLevel
    detection_latency: float = Field(..., ge=0.0, description="Detection latency measured in milliseconds")
    response_action: ResponseAction = ResponseAction.ALERT
    verification_status: VerificationStatus = VerificationStatus.PENDING
    trigger_details: Optional[Dict[str, Any]] = None
    store_audio: bool = Field(default=False, description="Whether raw audio snippet is stored (default False)")


class IncidentInDB(BaseModel):
    incident_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prediction: PredictionType
    confidence: float
    threat_level: ThreatLevel
    detection_latency: float
    response_action: ResponseAction
    verification_status: VerificationStatus
    trigger_details: Dict[str, Any] = Field(default_factory=dict)
    store_audio: bool = False
    audio_snippet_path: Optional[str] = None


class IncidentResponse(BaseModel):
    incident_id: str
    session_id: str
    timestamp: datetime
    prediction: PredictionType
    confidence: float
    threat_level: ThreatLevel
    detection_latency: float
    response_action: ResponseAction
    verification_status: VerificationStatus
    trigger_details: Dict[str, Any] = Field(default_factory=dict)
    store_audio: bool

    class Config:
        from_attributes = True

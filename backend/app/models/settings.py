"""
Settings models and schemas for system configuration.
Managed exclusively by Administrator users.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SystemSettings(BaseModel):
    detection_threshold: float = Field(
        default=0.75, gt=0.5, le=0.99,
        description="Confidence threshold to trigger deepfake classification and session restriction"
    )
    audio_window_length: float = Field(
        default=2.0, ge=0.5, le=5.0,
        description="Duration of rolling audio analysis window in seconds"
    )
    vad_sensitivity: int = Field(
        default=2, ge=0, le=3,
        description="Voice Activity Detector aggressiveness/sensitivity mode (0-3)"
    )
    demo_mode: bool = Field(
        default=True,
        description="Toggle between Synthetic Demo Fallback mode and production PyTorch ML mode"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


class SettingsUpdate(BaseModel):
    detection_threshold: Optional[float] = Field(None, gt=0.5, le=0.99)
    audio_window_length: Optional[float] = Field(None, ge=0.5, le=5.0)
    vad_sensitivity: Optional[int] = Field(None, ge=0, le=3)
    demo_mode: Optional[bool] = None

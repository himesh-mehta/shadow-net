"""
System Settings router.
Provides configuration access and modification restricted exclusively to Administrators.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.db import get_db
from app.routers.auth import require_roles
from app.models.user import UserRole, UserInDB
from app.models.settings import SystemSettings, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SystemSettings)
async def get_system_settings(
    current_user: UserInDB = Depends(require_roles(UserRole.ADMIN)),
    db=Depends(get_db),
):
    """
    Retrieve current system settings (Administrator only).
    """
    settings_doc = await db.settings.find_one({"scope": "global"})
    if settings_doc:
        return SystemSettings(
            detection_threshold=settings_doc.get("detection_threshold", 0.75),
            audio_window_length=settings_doc.get("audio_window_length", 2.0),
            vad_sensitivity=settings_doc.get("vad_sensitivity", 2),
            demo_mode=settings_doc.get("demo_mode", True),
            updated_at=settings_doc.get("updated_at", datetime.utcnow()),
            updated_by=settings_doc.get("updated_by"),
        )

    # Fallback to default env settings
    env_settings = get_settings()
    return SystemSettings(
        detection_threshold=env_settings.DETECTION_THRESHOLD,
        audio_window_length=env_settings.AUDIO_WINDOW_SECONDS,
        vad_sensitivity=env_settings.VAD_SENSITIVITY,
        demo_mode=env_settings.DEMO_MODE,
        updated_at=datetime.utcnow(),
        updated_by="system_default",
    )


@router.put("", response_model=SystemSettings)
async def update_system_settings(
    payload: SettingsUpdate,
    current_user: UserInDB = Depends(require_roles(UserRole.ADMIN)),
    db=Depends(get_db),
):
    """
    Update system detection threshold, audio window length, VAD sensitivity,
    or demo/ML mode toggle (Administrator only).
    """
    # Fetch existing
    existing = await db.settings.find_one({"scope": "global"})
    env_settings = get_settings()

    current_threshold = existing.get("detection_threshold", env_settings.DETECTION_THRESHOLD) if existing else env_settings.DETECTION_THRESHOLD
    current_window = existing.get("audio_window_length", env_settings.AUDIO_WINDOW_SECONDS) if existing else env_settings.AUDIO_WINDOW_SECONDS
    current_vad = existing.get("vad_sensitivity", env_settings.VAD_SENSITIVITY) if existing else env_settings.VAD_SENSITIVITY
    current_demo = existing.get("demo_mode", env_settings.DEMO_MODE) if existing else env_settings.DEMO_MODE

    now = datetime.utcnow()
    new_data = {
        "scope": "global",
        "detection_threshold": payload.detection_threshold if payload.detection_threshold is not None else current_threshold,
        "audio_window_length": payload.audio_window_length if payload.audio_window_length is not None else current_window,
        "vad_sensitivity": payload.vad_sensitivity if payload.vad_sensitivity is not None else current_vad,
        "demo_mode": payload.demo_mode if payload.demo_mode is not None else current_demo,
        "updated_at": now,
        "updated_by": current_user.username,
    }

    await db.settings.update_one(
        {"scope": "global"},
        {"$set": new_data},
        upsert=True,
    )

    return SystemSettings(**new_data)

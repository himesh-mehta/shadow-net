"""
MFA Verification Router for SHADOW-NET.
Provides prototype identity verification endpoints:
- POST /verify/request-otp
- POST /verify

DISCLAIMER:
This MFA verification flow is a simulated development prototype. It demonstrates
session recovery following deepfake restriction without connecting to real telecommunications
or third-party SMS/voice infrastructure.
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_db
from app.routers.auth import get_current_user
from app.models.user import UserInDB
from app.services.incident_service import (
    request_mfa_otp,
    verify_mfa_otp,
    PROTOTYPE_MFA_DISCLAIMER,
)

router = APIRouter(prefix="/verify", tags=["MFA Verification Simulation"])


class OTPRequestPayload(BaseModel):
    session_id: str = Field(..., description="ID of the restricted session requiring verification")


class OTPVerifyPayload(BaseModel):
    session_id: str = Field(..., description="ID of the restricted session")
    otp_code: str = Field(..., min_length=4, max_length=8, description="Submitted OTP code")


@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(
    payload: OTPRequestPayload,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Generate and dispatch a prototype MFA verification code for a restricted test session.
    In development mode, the OTP is returned directly in the response payload.
    """
    try:
        result = await request_mfa_otp(payload.session_id, current_user.id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("", status_code=status.HTTP_200_OK)
async def verify_code(
    payload: OTPVerifyPayload,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Validate the submitted MFA code. On success, lifts the session restriction,
    restores session status to 'active', and marks pending incidents as 'VERIFIED'.
    """
    result = await verify_mfa_otp(payload.session_id, payload.otp_code, db)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("detail", "Verification failed.")
        )
    return result

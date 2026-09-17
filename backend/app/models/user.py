"""
User models and schemas with role-based access controls.
Roles supported: Administrator, Security Analyst, User.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "Administrator"
    ANALYST = "Security Analyst"
    USER = "User"


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=6, description="Raw password (will be hashed with bcrypt)")
    role: UserRole = Field(default=UserRole.USER, description="Assigned role")


class UserLogin(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Raw password")


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    username: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None

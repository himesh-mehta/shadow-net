"""
Authentication module for SHADOW-NET.
Provides JWT-based authentication and role-based access control (RBAC).
Supported roles: Administrator, Security Analyst, User.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.config import get_settings
from app.db import get_db
from app.models.user import (
    UserRole,
    UserRegister,
    UserLogin,
    UserResponse,
    UserInDB,
    Token,
    TokenData,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> UserInDB:
    """Dependency to extract and validate the JWT Bearer token."""
    settings = get_settings()
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role_str: str = payload.get("role")
        if user_id is None or username is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, username=username, role=UserRole(role_str) if role_str else None)
    except (JWTError, ValueError):
        raise credentials_exception

    user_doc = await db.users.find_one({"id": token_data.user_id})
    if user_doc is None:
        raise credentials_exception

    user = UserInDB(**user_doc)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory to enforce role-based access control."""
    def role_checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[r.value for r in allowed_roles]}, user has role: '{current_user.role.value}'"
            )
        return current_user
    return role_checker


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db=Depends(get_db)):
    """
    Register a new user with an assigned role.
    Roles: Administrator, Security Analyst, User.
    """
    # Check if username exists
    existing_username = await db.users.find_one({"username": payload.username})
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered."
        )

    # Check if email exists
    existing_email = await db.users.find_one({"email": payload.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered."
        )

    now = datetime.utcnow()
    user_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(payload.password)

    user_record = {
        "id": user_id,
        "username": payload.username,
        "email": payload.email,
        "hashed_password": hashed_pwd,
        "role": payload.role.value,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    await db.users.insert_one(user_record)

    return UserResponse(
        id=user_id,
        username=payload.username,
        email=payload.email,
        role=payload.role,
        is_active=True,
        created_at=now,
    )


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db=Depends(get_db)):
    """
    Authenticate user credentials and issue a signed JWT access token.
    """
    # Allow login by username or email
    user_doc = await db.users.find_one({
        "$or": [{"username": payload.username}, {"email": payload.username}]
    })

    if not user_doc or not verify_password(payload.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated."
        )

    role_val = user_doc["role"]
    token_payload = {
        "sub": user_doc["id"],
        "username": user_doc["username"],
        "email": user_doc["email"],
        "role": role_val,
    }

    token = create_access_token(data=token_payload)

    return Token(
        access_token=token,
        token_type="bearer",
        role=UserRole(role_val),
        user_id=user_doc["id"],
        username=user_doc["username"],
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Retrieve the profile of the currently authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )

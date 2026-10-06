"""
backend/routes/auth.py
Authentication and user profile endpoints.
Provides register, login, logout, me, and profile management with
Argon2 password hashing, secure httpOnly JWT cookies, and rate limiting.
"""

import re
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from backend.database import get_db
import backend.models as models
from backend.schemas.schemas import (
    RegisterRequest,
    LoginRequest,
    UserProfileSchema,
    UserResponse,
)
from backend.services.auth_service import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    enforce_rate_limit,
    get_current_user,
)
from backend.config import (
    AUTH_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ENVIRONMENT,
)

logger = logging.getLogger("interview_system.auth")
router = APIRouter(tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _set_auth_cookie(response: Response, token: str) -> None:
    """Sets secure httpOnly authentication cookie."""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=(ENVIRONMENT == "production"),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clears authentication cookie."""
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        samesite="lax",
        httponly=True,
        path="/",
    )


def _build_profile_response(profile: Optional[models.UserProfile]) -> Optional[UserProfileSchema]:
    if not profile:
        return None
    return UserProfileSchema(
        target_role=profile.target_role,
        domain=profile.domain,
        experience_level=profile.experience_level,
        university=profile.university,
        graduation_year=profile.graduation_year,
        current_status=profile.current_status,
        target_companies=profile.target_companies or [],
        interview_goal=profile.interview_goal,
        weekly_practice_goal=profile.weekly_practice_goal,
    )


@router.post("/auth/register")
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account with Argon2 password hashing.
    Enforces password constraints and rate limiting.
    Sets httpOnly session cookie on success.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"register:{client_ip}", max_attempts=10, window_seconds=60)

    clean_email = data.email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    pwd_error = validate_password_strength(data.password)
    if pwd_error:
        raise HTTPException(status_code=400, detail=pwd_error)

    # Check for existing email
    existing = db.query(models.User).filter(models.User.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Hash password and create user
    hashed = hash_password(data.password)
    user = models.User(
        email=clean_email,
        password_hash=hashed,
        full_name=data.full_name.strip() if data.full_name else None,
    )
    db.add(user)
    db.flush()

    # Create empty user profile
    profile = models.UserProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)

    return {
        "message": "Account registered successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile": _build_profile_response(profile),
        }
    }


@router.post("/auth/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials and sets httpOnly session cookie.
    Enforces rate limiting and uniform error reporting to prevent account enumeration.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"login:{client_ip}", max_attempts=10, window_seconds=60)

    clean_email = data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()

    # Uniform error response for any auth failure
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)

    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()

    return {
        "message": "Logged in successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile": _build_profile_response(profile),
        }
    }


@router.post("/auth/logout")
def logout(response: Response):
    """Logs out user by clearing the httpOnly session cookie."""
    _clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
def get_me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns authenticated user identity and profile."""
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "profile": _build_profile_response(profile),
    }


@router.get("/profile")
def get_profile(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns current user profile."""
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
    if not profile:
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _build_profile_response(profile)


@router.put("/profile")
def update_profile(
    data: UserProfileSchema,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates current user profile."""
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
    if not profile:
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, val)

    db.commit()
    db.refresh(profile)

    return {
        "message": "Profile updated successfully",
        "profile": _build_profile_response(profile)
    }

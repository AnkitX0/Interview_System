"""
backend/services/auth_service.py
Authentication, password security with Argon2, JWT token handling,
session cookie management, and user authentication dependencies.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
import time
from collections import defaultdict

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
import jwt
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.config import (
    SECRET_KEY,
    ALGORITHM,
    AUTH_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.database import get_db
import backend.models as models

ph = PasswordHasher()

# ---------------------------------------------------------------------------
# Rate Limiting (In-memory token bucket per client key)
# ---------------------------------------------------------------------------
_rate_limits: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(key: str, max_attempts: int = 10, window_seconds: int = 60) -> bool:
    """
    In-memory rate limiter.
    Returns True if allowed, False if limit exceeded.
    """
    now = time.time()
    cutoff = now - window_seconds
    timestamps = [t for t in _rate_limits[key] if t > cutoff]
    _rate_limits[key] = timestamps

    if len(timestamps) >= max_attempts:
        return False

    _rate_limits[key].append(now)
    return True


def enforce_rate_limit(key: str, max_attempts: int = 10, window_seconds: int = 60) -> None:
    """Enforces rate limit, raising HTTP 429 if exceeded."""
    if not check_rate_limit(key, max_attempts, window_seconds):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait a moment before trying again."
        )


# ---------------------------------------------------------------------------
# Password Validation & Hashing
# ---------------------------------------------------------------------------
TRIVIAL_PASSWORDS = {
    "password123",
    "1234567890",
    "0987654321",
    "qwertyuiop",
    "abcdefghij",
    "password1234",
    "iloveyou123",
}


def validate_password_strength(password: str) -> Optional[str]:
    """
    Validates password against length and trivial weakness constraints.
    Does NOT impose arbitrary composition rules (uppercase, special char, etc.).
    Returns error string if invalid, None if valid.
    """
    if len(password) < 10:
        return "Password must be at least 10 characters long"

    if len(set(password)) <= 1:
        return "Password cannot consist of a single repeated character"

    if password.isdigit():
        return "Password cannot consist solely of digits"

    if password.lower() in TRIVIAL_PASSWORDS:
        return "Password is too trivial; please choose a stronger password"

    return None


def hash_password(password: str) -> str:
    """Hashes a password with Argon2-cffi. Never logs or leaks plaintext."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a candidate password against an Argon2 hash in constant time."""
    try:
        return ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ---------------------------------------------------------------------------
# JWT Token Handling
# ---------------------------------------------------------------------------
def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """Decodes a JWT access token and returns the user_id if valid, None otherwise."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        return int(user_id_str)
    except (jwt.PyJWTError, ValueError):
        return None


# ---------------------------------------------------------------------------
# FastAPI Auth Dependencies
# ---------------------------------------------------------------------------
def extract_token_from_request(request: Request) -> Optional[str]:
    """Extracts auth token from httpOnly cookie or Authorization Bearer header."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    return token


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> models.User:
    """
    FastAPI dependency requiring authentication.
    Raises 401 if unauthenticated or token is expired/invalid.
    """
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")

    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """FastAPI dependency that returns user if authenticated, or None if not."""
    token = extract_token_from_request(request)
    if not token:
        return None

    user_id = decode_access_token(token)
    if not user_id:
        return None

    return db.query(models.User).filter(models.User.id == user_id).first()

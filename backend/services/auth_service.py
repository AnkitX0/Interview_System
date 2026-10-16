"""
backend/services/auth_service.py
Authentication, password security with Argon2, JWT token handling,
session cookie management, and user authentication dependencies.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
import time
import re
import secrets
import hashlib
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
SPECIAL_CHAR_REGEX = re.compile(r"""[!@#$%^&*(),.?":{}|<>\-_=+[\]~`/\\';]""")


def validate_password_strength(password: str) -> Optional[str]:
    """
    Enforces production password policy:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    - Non-trivial (not all identical characters)
    Returns error string if invalid, None if valid.
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long."

    if len(set(password)) <= 1:
        return "Password cannot consist of a single repeated character."

    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."

    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter."

    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."

    if not SPECIAL_CHAR_REGEX.search(password):
        return "Password must contain at least one special character."

    return None


def hash_password(password: str) -> str:
    """Hashes a password with Argon2-cffi. Never logs or leaks plaintext."""
    return ph.hash(password)


# ---------------------------------------------------------------------------
# Cryptographic Token Helpers
# ---------------------------------------------------------------------------
def generate_verification_otp() -> str:
    """Generates a cryptographically secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_otp(otp: str) -> str:
    """Hashes a verification OTP using SHA-256 for secure database storage."""
    return hashlib.sha256(otp.strip().encode("utf-8")).hexdigest()


def generate_verification_token() -> str:
    """Generates a cryptographically random, single-use URL-safe verification token (or OTP)."""
    return generate_verification_otp()


def hash_verification_token(token: str) -> str:
    """Hashes a verification token or OTP using SHA-256 for secure database storage."""
    return hash_verification_otp(token)


def generate_password_reset_token() -> str:
    """Generates a cryptographically random, single-use URL-safe password reset token."""
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    """Hashes a password reset token using SHA-256 for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
# Security Questions for Password Recovery
# ---------------------------------------------------------------------------
ALLOWED_SECURITY_QUESTIONS = [
    "What is your favorite movie?",
    "What was your childhood nickname?",
    "What was the name of your first pet?",
    "What was the first concert you attended?",
    "What was the name of your childhood best friend?",
]


def normalize_security_answer(answer: Optional[str]) -> str:
    """
    Normalizes a security answer consistently:
    - Strips leading and trailing whitespace
    - Condenses internal multiple whitespaces
    - Lowercases for consistent case-insensitive comparison
    """
    if not answer:
        return ""
    return " ".join(answer.strip().lower().split())


def hash_security_answer(answer: str) -> str:
    """Hashes a normalized security answer with Argon2. Never stores or logs plaintext."""
    normalized = normalize_security_answer(answer)
    return ph.hash(normalized)


def verify_security_answer(plain_answer: str, hashed_answer: str) -> bool:
    """Verifies a candidate security answer against the stored Argon2 hash in constant time."""
    if not plain_answer or not hashed_answer:
        return False
    normalized = normalize_security_answer(plain_answer)
    try:
        return ph.verify(hashed_answer, normalized)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


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

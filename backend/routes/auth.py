"""
backend/routes/auth.py
Authentication and user profile endpoints.
Provides register, login, logout, me, and profile management with
Argon2 password hashing, secure httpOnly JWT cookies, and rate limiting.
"""

import re
import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from datetime import datetime, timedelta, timezone
from backend.database import get_db
import backend.models as models
from backend.schemas.schemas import (
    RegisterRequest,
    LoginRequest,
    RecoveryChallengeRequest,
    RecoveryVerifyAnswerRequest,
    RecoveryResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserProfileSchema,
    UserResponse,
    ConsentInput,
    PasswordConfirmRequest,
)
from backend.services.auth_service import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    enforce_rate_limit,
    check_rate_limit,
    ALLOWED_SECURITY_QUESTIONS,
    normalize_security_answer,
    hash_security_answer,
    verify_security_answer,
    generate_password_reset_token,
    hash_password_reset_token,
    get_current_user,
)
from backend.config import (
    AUTH_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_COOKIE_SAMESITE,
    AUTH_COOKIE_SECURE,
    ENVIRONMENT,
    PRIVACY_POLICY_VERSION,
    VERIFICATION_TOKEN_EXPIRE_MINUTES,
    VERIFICATION_OTP_EXPIRE_MINUTES,
    VERIFICATION_MAX_ATTEMPTS,
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    REQUIRE_EMAIL_VERIFICATION,
)

logger = logging.getLogger("interview_system.auth")
router = APIRouter(tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@gmail\.com$")


def mask_email_address(email: str) -> str:
    """Masks an email for safe display (e.g. j***e@gmail.com)."""
    if not email or "@" not in email:
        return email or ""
    parts = email.split("@")
    local, domain = parts[0], parts[1]
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    prefix = local[:2]
    suffix = local[-1]
    return f"{prefix}{'*' * max(3, len(local) - 3)}{suffix}@{domain}"


def validate_full_name(name: Optional[str]) -> Optional[str]:
    """Validates full name for registration: required, trimmed, min 2 chars, contains letters."""
    if not name or not name.strip():
        return "Please enter your name."
    trimmed = name.strip()
    if len(trimmed) < 2:
        return "Please enter your name."
    if not any(c.isalpha() for c in trimmed):
        return "Please enter your name."
    return None


def validate_gmail_address(email: str) -> Optional[str]:
    """Validates that email is a syntactically valid address with domain @gmail.com strictly."""
    if not email:
        return "Please use a Gmail address."
    clean = email.strip().lower()
    if not EMAIL_REGEX.match(clean):
        return "Please use a Gmail address."
    parts = clean.split("@")
    if len(parts) != 2:
        return "Please use a Gmail address."
    local_part, domain = parts
    if not local_part or domain != "gmail.com":
        return "Please use a Gmail address."
    if not GMAIL_REGEX.match(clean):
        return "Please use a Gmail address."
    return None


def _get_cookie_security_params():
    samesite = (AUTH_COOKIE_SAMESITE or "lax").lower().strip()
    if samesite not in ("lax", "strict", "none"):
        samesite = "lax"
    secure = bool(AUTH_COOKIE_SECURE or samesite == "none")
    return samesite, secure


def _set_auth_cookie(response: Response, token: str, remember_me: bool = False) -> None:
    """Sets secure httpOnly authentication cookie with optional 30-day persistence."""
    samesite, secure = _get_cookie_security_params()
    max_age = (30 * 24 * 3600) if remember_me else (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=True,
        samesite=samesite,
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clears authentication cookie."""
    samesite, secure = _get_cookie_security_params()
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=True,
        samesite=samesite,
    )


def _build_profile_response(profile: Optional[models.UserProfile], user: Optional[models.User] = None) -> Optional[UserProfileSchema]:
    if not profile:
        return None
    full_name = user.full_name if user else (profile.user.full_name if getattr(profile, "user", None) else None)
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
        phone=profile.phone,
        location=profile.location,
        bio=profile.bio,
        degree=profile.degree,
        skills_categorized=profile.skills_categorized or {},
        professional_links=profile.professional_links or {},
        full_name=full_name,
    )


@router.post("/auth/register")
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account with strict Gmail validation, Argon2 password hashing,
    and security question selection for password recovery.
    Account is immediately activated without email verification.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"register:{client_ip}", max_attempts=30, window_seconds=60)

    # 1. Full name validation
    name_error = validate_full_name(data.full_name)
    if name_error:
        raise HTTPException(status_code=400, detail=name_error)

    # 2. Gmail validation
    clean_email = data.email.strip().lower()
    gmail_error = validate_gmail_address(clean_email)
    if gmail_error:
        raise HTTPException(status_code=400, detail=gmail_error)

    # 3. Password strength validation
    pwd_error = validate_password_strength(data.password)
    if pwd_error:
        raise HTTPException(status_code=400, detail=pwd_error)

    # 4. Security question validation (if provided, must be from allowed list)
    if data.security_question:
        if data.security_question not in ALLOWED_SECURITY_QUESTIONS:
            raise HTTPException(
                status_code=400,
                detail="Please select a valid security question from the provided list."
            )
        if not data.security_answer or not data.security_answer.strip():
            raise HTTPException(
                status_code=400,
                detail="Please enter your answer and remember it for account recovery."
            )

    # 5. Existing account check (prevents duplicate accounts)
    existing = db.query(models.User).filter(models.User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="If an account already exists for this address, please sign in or recover your password."
        )

    clean_name = data.full_name.strip() if data.full_name else None
    hashed_pwd = hash_password(data.password)
    hashed_answer = hash_security_answer(data.security_answer) if data.security_answer else None
    now = datetime.now(timezone.utc)

    user = models.User(
        email=clean_email,
        password_hash=hashed_pwd,
        full_name=clean_name,
        email_verified=True,
        security_question=data.security_question,
        security_answer_hash=hashed_answer,
        recovery_attempts=0,
        verification_token_hash=None,
        verification_expires_at=None,
        verification_sent_at=None,
        verification_attempts=0,
        verification_used_at=now,
    )
    db.add(user)
    db.flush()

    profile = models.UserProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)

    logger.info("New registration activated immediately for %s (id=%d)", clean_email, user.id)

    return {
        "message": "Account created successfully.",
        "email": clean_email,
        "verification_required": False,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile": _build_profile_response(profile, user),
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
    Supports remember_me (30-day session) and directs unregistered users to register first.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"login:{client_ip}", max_attempts=15, window_seconds=60)

    clean_email = data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="No account found with this email. Please register first."
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    remember = bool(getattr(data, "remember_me", False))
    expires_delta = timedelta(days=30) if remember else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(user.id, expires_delta=expires_delta)
    _set_auth_cookie(response, token, remember_me=remember)

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


# ---------------------------------------------------------------------------
# Security Question Password Recovery Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/recovery/challenge")
def recovery_challenge(
    data: RecoveryChallengeRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Returns the user's registered security question for account recovery.
    Rate limited per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"recovery_challenge:{client_ip}", max_attempts=15, window_seconds=60)

    clean_email = data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email address. Please check your email or create an account."
        )

    if not user.security_question or not user.security_answer_hash:
        raise HTTPException(
            status_code=400,
            detail="No security question is configured for this account. Please sign in with your credentials or contact support."
        )

    return {
        "status": "ok",
        "email": user.email,
        "question": user.security_question,
        "security_question": user.security_question,
        "masked_email": mask_email_address(user.email),
    }


@router.post("/auth/recovery/verify-answer")
def recovery_verify_answer(
    data: RecoveryVerifyAnswerRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verifies candidate security answer against stored Argon2 hash.
    Enforces maximum 5 attempts lockout. Returns single-use 15-minute recovery token on success.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"recovery_verify:{client_ip}", max_attempts=15, window_seconds=60)

    clean_email = data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()

    if not user or not user.security_question or not user.security_answer_hash:
        raise HTTPException(
            status_code=400,
            detail="Invalid recovery request or no security question configured."
        )

    # Check recovery attempt limits (max 5)
    attempts = getattr(user, "recovery_attempts", 0) or 0
    if attempts >= 5:
        raise HTTPException(
            status_code=429,
            detail="Maximum recovery attempts exceeded. Please try again later."
        )

    candidate_answer = (data.answer or data.security_answer or "").strip()
    if not candidate_answer:
        raise HTTPException(
            status_code=422,
            detail="Security answer is required."
        )

    # Ensure selected question matches the question saved during registration if supplied
    candidate_question = (data.security_question or data.question or "").strip()
    if candidate_question and candidate_question.lower() != (user.security_question or "").strip().lower():
        user.recovery_attempts = attempts + 1
        db.commit()
        remaining = max(0, 5 - user.recovery_attempts)
        if remaining == 0:
            raise HTTPException(
                status_code=429,
                detail="Maximum recovery attempts exceeded. Please try again later."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Selected security question does not match account records. {remaining} attempt(s) remaining."
        )

    is_valid = verify_security_answer(candidate_answer, user.security_answer_hash)
    if not is_valid:
        user.recovery_attempts = attempts + 1
        db.commit()
        remaining = max(0, 5 - user.recovery_attempts)
        if remaining == 0:
            raise HTTPException(
                status_code=429,
                detail="Maximum recovery attempts exceeded. Please try again later."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect security answer. {remaining} attempt(s) remaining."
        )

    # Reset attempts on success and issue single-use recovery token
    user.recovery_attempts = 0
    raw_token = generate_password_reset_token()
    token_hash = hash_password_reset_token(raw_token)
    user.password_reset_token_hash = token_hash
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    user.password_reset_used_at = None
    db.commit()

    return {
        "message": "Security answer verified successfully.",
        "recovery_token": raw_token,
    }


@router.post("/auth/recovery/reset-password")
def recovery_reset_password(
    data: RecoveryResetPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Updates user password using single-use recovery token issued after security answer verification.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"recovery_reset:{client_ip}", max_attempts=10, window_seconds=60)

    pwd_err = validate_password_strength(data.new_password)
    if pwd_err:
        raise HTTPException(status_code=400, detail=pwd_err)

    clean_email = data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid recovery request.")

    token_hash = hash_password_reset_token(data.recovery_token.strip())
    if user.password_reset_token_hash != token_hash:
        raise HTTPException(status_code=400, detail="Recovery session is invalid or has expired.")

    now = datetime.now(timezone.utc)
    if user.password_reset_expires_at:
        exp = user.password_reset_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise HTTPException(status_code=400, detail="Recovery session has expired. Please restart recovery.")

    if user.password_reset_used_at is not None:
        raise HTTPException(status_code=400, detail="Recovery session has already been used.")

    # Update password and consume token atomically
    user.password_hash = hash_password(data.new_password)
    user.password_reset_used_at = now
    user.password_reset_token_hash = None
    db.commit()

    _clear_auth_cookie(response)
    logger.info("Password successfully recovered and updated for user %s", user.email)

    return {
        "message": "Password updated successfully. You can now sign in with your new password.",
        "success": True,
    }


@router.get("/auth/validate-reset-token")
def validate_reset_token(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Validates a password reset token before rendering the reset form.
    Checks existence, single-use state, and expiration.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"val_reset:{client_ip}", max_attempts=30, window_seconds=60)

    raw_token = token.strip() if token else ""
    if not raw_token:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    token_hash = hash_password_reset_token(raw_token)
    user = db.query(models.User).filter(models.User.password_reset_token_hash == token_hash).first()

    if not user:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    if user.password_reset_used_at is not None:
        raise HTTPException(status_code=400, detail="This password reset link has already been used.")

    now = datetime.now(timezone.utc)
    if user.password_reset_expires_at:
        expires_at = user.password_reset_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(status_code=400, detail="This password reset link has expired.")

    return {
        "valid": True,
        "email": mask_email_address(user.email),
    }


@router.post("/auth/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Validates single-use password reset token and updates user password with Argon2 hashing.
    Invalidates used token and existing session cookie.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"reset_ip:{client_ip}", max_attempts=10, window_seconds=60)

    # Validate new password policy
    pwd_err = validate_password_strength(data.new_password)
    if pwd_err:
        raise HTTPException(status_code=400, detail=pwd_err)

    raw_token = data.token.strip()
    if not raw_token:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    token_hash = hash_password_reset_token(raw_token)
    user = db.query(models.User).filter(models.User.password_reset_token_hash == token_hash).first()

    if not user:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    if user.password_reset_used_at is not None:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    now = datetime.now(timezone.utc)
    if user.password_reset_expires_at:
        expires_at = user.password_reset_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    # Apply new password hash and atomically mark token used
    updated_rows = db.query(models.User).filter(
        models.User.id == user.id,
        models.User.password_reset_used_at.is_(None)
    ).update({
        models.User.password_hash: hash_password(data.new_password),
        models.User.password_reset_used_at: now,
        models.User.password_reset_token_hash: None
    }, synchronize_session="fetch")
    db.commit()

    if updated_rows == 0:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")

    # Clear any active auth cookie to force re-authentication with new password
    _clear_auth_cookie(response)

    logger.info("Password successfully reset for user id=%d", user.id)

    return {
        "message": "Your password has been updated.",
        "success": True,
    }



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

    return _build_profile_response(profile, user=user)


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

    update_dict = data.model_dump(exclude_unset=True)
    if "full_name" in update_dict and update_dict["full_name"] is not None:
        user.full_name = update_dict.pop("full_name")

    for field, val in update_dict.items():
        if hasattr(profile, field):
            setattr(profile, field, val)

    db.commit()
    db.refresh(profile)
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "profile": _build_profile_response(profile, user=user)
    }


# =========================
# PRIVACY CONSENT MANAGEMENT
# =========================
@router.get("/consent")
def get_consent_records(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all privacy consent records for the current user."""
    records = db.query(models.ConsentRecord).filter(
        models.ConsentRecord.user_id == user.id
    ).order_by(models.ConsentRecord.id.desc()).all()

    return [
        {
            "id": r.id,
            "consent_type": r.consent_type,
            "granted": r.granted,
            "policy_version": r.policy_version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/consent")
def record_consent(
    data: ConsentInput,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records user consent grant or withdrawal for specific processing activity."""
    record = models.ConsentRecord(
        user_id=user.id,
        consent_type=data.consent_type,
        granted=data.granted,
        policy_version=data.policy_version or PRIVACY_POLICY_VERSION,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "Consent status recorded successfully",
        "consent": {
            "id": record.id,
            "consent_type": record.consent_type,
            "granted": record.granted,
            "policy_version": record.policy_version,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "timestamp": record.created_at.isoformat() if record.created_at else None,
        }
    }


# =========================
# DATA EXPORT & RIGHT TO BE FORGOTTEN
# =========================
@router.get("/auth/export")
def export_user_data(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports full user data as JSON per GDPR/CCPA data portability principles.
    Includes account profile, consent logs, resumes, sessions, and rubric evaluations.
    """
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
    consent_records = db.query(models.ConsentRecord).filter(models.ConsentRecord.user_id == user.id).all()
    resumes = db.query(models.Resume).filter(models.Resume.user_id == user.id).all()
    sessions = db.query(models.InterviewSession).filter(models.InterviewSession.user_id == user.id).all()

    sessions_data = []
    for s in sessions:
        score = db.query(models.SessionScore).filter(models.SessionScore.session_id == s.id).first()
        behavioral = db.query(models.BehavioralMetrics).filter(models.BehavioralMetrics.session_id == s.id).first()
        answers = db.query(models.InterviewAnswer).filter(models.InterviewAnswer.session_id == s.id).all()

        answers_data = []
        for a in answers:
            ev = db.query(models.AnswerEvaluation).filter(models.AnswerEvaluation.answer_id == a.id).first()
            vm = db.query(models.VoiceMetrics).filter(models.VoiceMetrics.answer_id == a.id).first()
            avm = db.query(models.AnswerVisualMetrics).filter(models.AnswerVisualMetrics.answer_id == a.id).first()
            answers_data.append({
                "answer_id": a.id,
                "question_id": a.question_id,
                "question_text": a.question_text,
                "transcript": a.transcript,
                "response_time": a.response_time,
                "duration_seconds": a.duration_seconds,
                "wpm": a.wpm,
                "filler_count": a.filler_count,
                "evaluation": {
                    "structure_score": ev.structure_score if ev else None,
                    "technical_score": ev.technical_score if ev else None,
                    "reasoning_score": ev.reasoning_score if ev else None,
                    "star_score": ev.star_score if ev else None,
                    "consistency_score": ev.consistency_score if ev else None,
                    "overall_score": ev.overall_score if ev else None,
                    "engine_used": ev.engine_used if ev else None,
                    "prompt_version": ev.prompt_version if ev else None,
                    "verification_risk_score": ev.verification_risk_score if ev else None,
                    "verification_risk_level": ev.verification_risk_level if ev else None,
                    "verification_risk_evidence": ev.verification_risk_evidence if ev else None,
                    "verification_risk_explanation": ev.verification_risk_explanation if ev else None,
                } if ev else None,
                "voice_metrics": {
                    "words_per_minute": vm.words_per_minute,
                    "filler_word_count": vm.filler_word_count,
                    "avg_pause_duration": vm.avg_pause_duration,
                    "longest_pause": vm.longest_pause,
                    "pause_count": vm.pause_count,
                    "silence_ratio": vm.silence_ratio,
                    "vocabulary_diversity_score": vm.vocabulary_diversity_score,
                    "speech_source": vm.speech_source,
                } if vm else None,
                "visual_metrics": {
                    "head_alignment_percent": avm.head_alignment_percent,
                    "blink_rate": avm.blink_rate,
                    "head_movement_variance": avm.head_movement_variance,
                    "face_visibility_ratio": avm.face_visibility_ratio,
                    "head_shift_count": avm.head_shift_count,
                    "frames_sampled": avm.frames_sampled,
                } if avm else None,
            })

        # Fetch Phase 3 session-level intelligence tables
        questions_data = [
            {
                "id": q.id,
                "sequence_order": q.sequence_order,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "source": q.source,
                "ladder_stage": q.ladder_stage,
                "difficulty": q.difficulty,
                "time_limit_seconds": q.time_limit_seconds,
                "generated_reason": q.generated_reason,
            }
            for q in s.questions_list
        ]

        decisions_data = [
            {
                "turn": d.turn,
                "decision": d.decision,
                "reason": d.reason,
                "inputs": d.inputs,
            }
            for d in s.decisions
        ]

        claim_consistencies_data = [
            {
                "claim_id": cc.claim_id,
                "label": cc.label,
                "evidence": cc.evidence,
                "answers_considered": cc.answers_considered,
            }
            for cc in s.claim_consistencies
        ]

        sessions_data.append({
            "session_id": s.id,
            "mode": s.mode,
            "difficulty": s.difficulty,
            "target_role": s.target_role,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "score": {
                "final_readiness_score": score.readiness_score,
                "delivery_score": score.behavioral_score,
                "communication_score": score.communication_score,
                "technical_score": score.technical_score,
                "resume_consistency_score": score.resume_consistency_score,
                "consistency_source": score.consistency_source,
            } if score else None,
            "behavioral_metrics": {
                "eye_contact_percent": behavioral.eye_contact_percent,
                "blink_rate": behavioral.blink_rate,
                "pause_rate": behavioral.pause_rate,
            } if behavioral else None,
            "questions": questions_data,
            "decisions": decisions_data,
            "claim_consistency": claim_consistencies_data,
            "answers": answers_data,
        })

    resumes_data = []
    for r in resumes:
        skills_val = []
        if r.skills:
            try:
                skills_val = json.loads(r.skills)
            except Exception:
                skills_val = [r.skills]

        skills_detailed = [
            {
                "name": sk.name,
                "category": sk.category,
                "confidence": sk.confidence,
                "evidenced": sk.evidenced,
            }
            for sk in r.skills_list
        ]

        projects_detailed = [
            {
                "title": p.title,
                "description": p.description,
                "technologies": p.technologies,
                "bullets": p.bullets,
            }
            for p in r.projects
        ]

        claims_detailed = [
            {
                "id": c.id,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "technologies": c.technologies,
                "has_metric": c.has_metric,
                "probe_priority": c.probe_priority,
                "reasons": c.reasons,
            }
            for c in r.claims
        ]

        flags_detailed = [
            {
                "flag_type": f.flag_type,
                "description": f.description,
                "severity": f.severity,
            }
            for f in r.flags
        ]

        resumes_data.append({
            "id": r.id,
            "filename": r.filename,
            "candidate_name": r.candidate_name,
            "skills": skills_val,
            "experience": r.experience,
            "education": r.education,
            "resume_score": r.resume_score,
            "role_fit_scores": r.role_fit_scores,
            "risk_areas": r.risk_areas,
            "summary": r.summary,
            "skills_list": skills_detailed,
            "projects": projects_detailed,
            "claims": claims_detailed,
            "flags": flags_detailed,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    practice_recs = db.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.user_id == user.id
    ).all()
    practice_recs_data = [
        {
            "id": pr.id,
            "source_session_id": pr.source_session_id,
            "weakness_type": pr.weakness_type,
            "dimension": pr.dimension,
            "priority": pr.priority,
            "rationale": pr.rationale,
            "practice_type": pr.practice_type,
            "target_count": pr.target_count,
            "difficulty": pr.difficulty,
            "status": pr.status,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "completed_at": pr.completed_at.isoformat() if pr.completed_at else None,
        }
        for pr in practice_recs
    ]

    prof_resp = _build_profile_response(profile)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "profile": prof_resp.model_dump() if prof_resp else None,
        "consent_records": [
            {
                "id": c.id,
                "consent_type": c.consent_type,
                "granted": c.granted,
                "policy_version": c.policy_version,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "timestamp": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consent_records
        ],
        "resumes": resumes_data,
        "interview_sessions": sessions_data,
        "practice_recommendations": practice_recs_data,
        "data_retention_policy": "Your data is kept until you delete it.",
    }


@router.delete("/auth/account")
def delete_account(
    data: PasswordConfirmRequest,
    response: Response,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes user account and cascades deletion of all associated
    personal data, profiles, consent records, resumes, interview sessions,
    answers, and derived scoring metrics.
    Requires password re-confirmation.
    """
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    user_id = user.id
    db.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.user_id == user_id
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()

    _clear_auth_cookie(response)

    return {
        "message": "Account and all associated personal data permanently deleted.",
        "user_id": user_id,
    }


if ENVIRONMENT != "production":
    @router.get("/auth/dev/latest-verification-email")
    def get_dev_verification_email(email: str):
        """Development-only endpoint for automated test suites to inspect the local development mailbox."""
        from backend.services.email_service import get_latest_dev_email, DEV_EMAIL_LOG
        record = get_latest_dev_email(email)
        if record:
            return record

        # Fallback to reading from dev_emails.log
        try:
            import os
            if os.path.exists(DEV_EMAIL_LOG):
                with open(DEV_EMAIL_LOG, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in reversed(lines):
                    if f"TO: {email.lower()}" in line.lower():
                        parts = line.strip().split(" | ")
                        token = parts[1].replace("TOKEN: ", "").strip()
                        link = parts[2].replace("LINK: ", "").strip()
                        return {"to_email": email, "token": token, "verification_link": link}
        except Exception:
            pass

        raise HTTPException(
            status_code=404,
            detail="No verification email found for this address in dev mailbox."
        )


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

from backend.database import get_db
import backend.models as models
from backend.schemas.schemas import (
    RegisterRequest,
    LoginRequest,
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
        policy_version=data.policy_version or "v1.0",
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
            })

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
            } if score else None,
            "behavioral_metrics": {
                "eye_contact_percent": behavioral.eye_contact_percent,
                "blink_rate": behavioral.blink_rate,
                "pause_rate": behavioral.pause_rate,
            } if behavioral else None,
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
        resumes_data.append({
            "id": r.id,
            "filename": r.filename,
            "candidate_name": r.candidate_name,
            "skills": skills_val,
            "experience": r.experience,
            "education": r.education,
            "resume_score": r.resume_score,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

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
    db.delete(user)
    db.commit()

    _clear_auth_cookie(response)

    return {
        "message": "Account and all associated personal data permanently deleted.",
        "user_id": user_id,
    }


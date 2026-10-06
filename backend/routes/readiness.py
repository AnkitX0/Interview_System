from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import backend.models as models
from backend.database import get_db
from backend.services.auth_service import get_current_user
from backend.services.readiness_engine import compute_longitudinal_readiness
from backend.services.comparability_service import filter_comparable_sessions

router = APIRouter(prefix="/readiness", tags=["Readiness Engine"])


@router.get("/current")
def get_current_readiness(
    target_threshold: Optional[float] = Query(80.0, description="Target readiness score threshold"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns candidate's longitudinal readiness profile, data-sufficiency confidence,
    trend, strongest/weakest dimensions, and baseline projection.
    """
    return compute_longitudinal_readiness(
        user_id=user.id,
        db=db,
        target_threshold=target_threshold or 80.0
    )


@router.get("/history")
def get_readiness_history(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns chronological history of completed session readiness scores with dimension breakdowns.
    """
    sessions = (
        db.query(models.InterviewSession)
        .filter(
            models.InterviewSession.user_id == user.id,
            models.InterviewSession.status == "completed"
        )
        .order_by(models.InterviewSession.created_at.asc(), models.InterviewSession.id.asc())
        .all()
    )

    if not sessions:
        return {"sessions": [], "total_count": 0}

    session_ids = [s.id for s in sessions]
    scores = (
        db.query(models.SessionScore)
        .filter(models.SessionScore.session_id.in_(session_ids))
        .all()
    )
    score_by_session = {sc.session_id: sc for sc in scores}

    latest_session = sessions[-1]
    comparable_sessions = filter_comparable_sessions(latest_session, sessions)
    comparable_ids = {s.id for s in comparable_sessions}

    history_items = []
    for s in sessions:
        sc = score_by_session.get(s.id)
        history_items.append({
            "session_id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "target_role": s.target_role,
            "mode": s.mode,
            "difficulty": s.difficulty,
            "is_comparable_to_latest": s.id in comparable_ids,
            "readiness_score": sc.readiness_score if sc else None,
            "communication_score": sc.communication_score if sc else None,
            "technical_score": sc.technical_score if sc else None,
            "delivery_score": sc.behavioral_score if sc else None,
            "resume_consistency_score": sc.resume_consistency_score if sc else None,
        })

    return {
        "sessions": history_items,
        "total_count": len(history_items),
        "comparable_to_latest_count": len(comparable_ids)
    }


@router.get("/forecast")
def get_readiness_forecast(
    target_threshold: Optional[float] = Query(80.0, description="Target readiness score threshold"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns transparent baseline projection and target gap status.
    Labeled explicitly as 'Baseline projection' - NOT 'AI prediction'.
    """
    res = compute_longitudinal_readiness(
        user_id=user.id,
        db=db,
        target_threshold=target_threshold or 80.0
    )
    return {
        "current_readiness": res.get("current_readiness"),
        "confidence": res.get("confidence"),
        "trend": res.get("trend"),
        "target": res.get("target"),
        "projection": res.get("projection"),
        "disclaimer": res.get("disclaimer")
    }

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import backend.models as models
from backend.database import get_db
from backend.services.auth_service import get_current_user
from backend.services.practice_recommendation_engine import (
    select_next_practice,
    VALID_PRACTICE_TYPES,
    WEAKNESS_TO_PRACTICE_MAP
)
from backend.services.question_selector import select_questions
from backend.services.practice_drill_service import select_distinct_practice_questions
from backend.services.comparability_service import is_comparable
from backend.services.scoring_engine import calculate_session_score

router = APIRouter(prefix="/practice", tags=["Targeted Practice"])


class StartPracticeRequest(BaseModel):
    recommendation_id: Optional[int] = None
    practice_type: str = Field(..., description="Targeted practice type e.g. TECHNICAL_DEPTH, COMMUNICATION")
    target_role: Optional[str] = "Software Engineer"
    difficulty: Optional[str] = "medium"
    question_count: Optional[int] = 5


@router.get("/recommendations")
def get_user_recommendations(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns active practice recommendations for the authenticated candidate.
    Generates dynamic recommendations if none exist.
    """
    recs = (
        db.query(models.PracticeRecommendation)
        .filter(models.PracticeRecommendation.user_id == user.id)
        .order_by(models.PracticeRecommendation.priority.asc(), models.PracticeRecommendation.created_at.desc())
        .all()
    )

    if not recs:
        # Dynamically generate and store recommendations
        select_next_practice(user_id=user.id, db=db, save_to_db=True)
        recs = (
            db.query(models.PracticeRecommendation)
            .filter(models.PracticeRecommendation.user_id == user.id)
            .order_by(models.PracticeRecommendation.priority.asc(), models.PracticeRecommendation.created_at.desc())
            .all()
        )

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "source_session_id": r.source_session_id,
            "weakness_type": r.weakness_type,
            "dimension": r.dimension,
            "priority": r.priority,
            "rationale": r.rationale,
            "practice_type": r.practice_type,
            "target_count": r.target_count,
            "difficulty": r.difficulty,
            "status": r.status,
            "decision_metadata": r.decision_metadata or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in recs
    ]


@router.post("/start")
def start_targeted_practice(
    data: StartPracticeRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Starts a targeted practice session mapping directly to existing interview infrastructure.
    Reuses question bank, probe ladder, scoring rubrics, and /next adaptive endpoints.
    """
    p_type = data.practice_type.strip().upper()
    if p_type not in VALID_PRACTICE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid practice_type '{p_type}'. Must be one of: {sorted(list(VALID_PRACTICE_TYPES))}"
        )

    # 1. Map practice type to session mode and question criteria
    session_mode = "technical"
    if p_type in ("COMMUNICATION", "STRUCTURED_ANSWER", "BEHAVIORAL_STAR"):
        session_mode = "behavioral"
    elif p_type == "PRESSURE_RESPONSE":
        session_mode = "pressure"

    time_limit = 45 if p_type == "PRESSURE_RESPONSE" else 90

    # 2. Create InterviewSession
    target_count = max(1, min(10, data.question_count or 5))
    session = models.InterviewSession(
        user_id=user.id,
        mode=session_mode,
        difficulty=data.difficulty or "medium",
        target_role=data.target_role or "Software Engineer",
        total_questions=target_count,
        current_question_index=0,
        status="in_progress"
    )
    db.add(session)
    db.flush()

    # 3. Update recommendation status if provided
    rec_obj = None
    if data.recommendation_id:
        rec_obj = db.query(models.PracticeRecommendation).filter_by(
            id=data.recommendation_id,
            user_id=user.id
        ).first()
        if rec_obj:
            rec_obj.status = "in_progress"

    # 4. Select initial questions from question bank
    category_map = {
        "TECHNICAL_DEPTH": "Technical",
        "TRADEOFF_REASONING": "Technical",
        "FOLLOWUP_DEFENSE": "Technical",
        "COMMUNICATION": "Behavioral",
        "STRUCTURED_ANSWER": "Behavioral",
        "BEHAVIORAL_STAR": "Behavioral",
        "PRESSURE_RESPONSE": "Pressure",
        "PROJECT_DEFENSE": "Technical",
        "RESUME_CLAIM_DEFENSE": "Technical",
    }
    target_category = category_map.get(p_type, "Technical")

    questions = select_distinct_practice_questions(
        db=db,
        user_id=user.id,
        practice_type=p_type,
        difficulty=data.difficulty or "medium",
        count=target_count,
        target_role=data.target_role or "Software Engineer"
    )

    for q in questions:
        q["time_limit_seconds"] = time_limit
        q["caption"] = f"Practice: {p_type.replace('_', ' ').title()}"

    # 5. Log practice session decision
    init_decision = models.InterviewDecision(
        session_id=session.id,
        turn=1,
        decision="START_PRACTICE",
        reason=f"Targeted practice started for '{p_type}' ({target_category}, {data.difficulty}). Time limit: {time_limit}s.",
        inputs={
            "practice_type": p_type,
            "recommendation_id": data.recommendation_id,
            "target_role": data.target_role,
            "difficulty": data.difficulty,
            "time_limit_seconds": time_limit
        }
    )
    db.add(init_decision)
    db.commit()

    return {
        "session_id": session.id,
        "practice_type": p_type,
        "mode": session_mode,
        "difficulty": data.difficulty or "medium",
        "target_role": data.target_role or "Software Engineer",
        "total_questions": len(questions),
        "time_limit_seconds": time_limit,
        "questions": questions,
        "recommendation_id": data.recommendation_id
    }


@router.post("/{session_id}/complete")
def complete_targeted_practice(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Completes a targeted practice session, updates recommendation status to 'completed',
    and generates a Before vs After comparison when comparable baseline data exists.
    """
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    session.status = "completed"

    # Find associated recommendation
    rec_obj = (
        db.query(models.PracticeRecommendation)
        .filter(
            models.PracticeRecommendation.user_id == user.id,
            models.PracticeRecommendation.status.in_(("in_progress", "pending"))
        )
        .order_by(models.PracticeRecommendation.created_at.desc())
        .first()
    )
    if rec_obj:
        rec_obj.status = "completed"
        rec_obj.completed_at = datetime.now(timezone.utc)

    # Fetch current session score
    curr_score = db.query(models.SessionScore).filter_by(session_id=session.id).first()
    curr_readiness = curr_score.readiness_score if curr_score else 75.0
    curr_tech = curr_score.technical_score if curr_score else 70.0
    curr_comm = curr_score.communication_score if curr_score else 70.0

    # Locate prior comparable session
    prior_sessions = (
        db.query(models.InterviewSession)
        .filter(
            models.InterviewSession.user_id == user.id,
            models.InterviewSession.id != session.id,
            models.InterviewSession.status == "completed"
        )
        .order_by(models.InterviewSession.created_at.desc())
        .all()
    )

    comparison = {
        "has_comparable_baseline": False,
        "summary": "Practice session completed successfully.",
        "before_score": None,
        "after_score": curr_readiness,
        "delta": None
    }

    for prior_s in prior_sessions:
        ok, _ = is_comparable(prior_s, session)
        if ok:
            prior_sc = db.query(models.SessionScore).filter_by(session_id=prior_s.id).first()
            if prior_sc:
                before_val = prior_sc.readiness_score or 70.0
                after_val = curr_readiness
                delta = round(after_val - before_val, 1)

                dim_label = "Readiness"
                if rec_obj and rec_obj.dimension == "technical":
                    before_val = prior_sc.technical_score or 70.0
                    after_val = curr_tech
                    delta = round(after_val - before_val, 1)
                    dim_label = "Technical Depth"
                elif rec_obj and rec_obj.dimension == "communication":
                    before_val = prior_sc.communication_score or 70.0
                    after_val = curr_comm
                    delta = round(after_val - before_val, 1)
                    dim_label = "Communication"

                comparison = {
                    "has_comparable_baseline": True,
                    "baseline_session_id": prior_s.id,
                    "dimension": dim_label,
                    "before_score": before_val,
                    "after_score": after_val,
                    "delta": delta,
                    "summary": f"Before: {dim_label} = {before_val}, After: {dim_label} = {after_val}, Result: {delta:+.1f} points."
                }
                break

    db.commit()

    return {
        "session_id": session.id,
        "status": "completed",
        "practice_recommendation_id": rec_obj.id if rec_obj else None,
        "comparison": comparison
    }

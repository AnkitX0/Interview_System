from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.models import models
from backend.services.comparability_service import filter_comparable_sessions


def calculate_improvement_velocity(
    user_id: int,
    db: Session,
    target_session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes longitudinal improvement velocity across comparable interview sessions for a candidate.

    Guarantees:
    - Never calculates slope across unrelated interview modes/roles.
    - Requires at least 2 comparable completed sessions; returns 'insufficient_data' otherwise.
    - Avoids causal overclaiming ("Performance improved across repeated practice sessions", never "Feature X caused").
    - Calculates overall and per-dimension velocity.
    """
    all_user_sessions = (
        db.query(models.InterviewSession)
        .filter(
            models.InterviewSession.user_id == user_id,
            models.InterviewSession.status == "completed"
        )
        .order_by(models.InterviewSession.created_at.asc(), models.InterviewSession.id.asc())
        .all()
    )

    if not all_user_sessions:
        return {
            "status": "insufficient_data",
            "message": "No completed sessions found for user.",
            "sessions_count": 0,
            "velocity": None,
            "velocity_per_session": None,
            "dimension_deltas": {}
        }

    # Reference session is either specified target_session_id or latest session
    if target_session_id:
        ref_session = next((s for s in all_user_sessions if s.id == target_session_id), all_user_sessions[-1])
    else:
        ref_session = all_user_sessions[-1]

    comparable_sessions = filter_comparable_sessions(ref_session, all_user_sessions)

    if len(comparable_sessions) < 2:
        return {
            "status": "insufficient_data",
            "message": f"Only {len(comparable_sessions)} comparable session found. Minimum 2 comparable sessions required to compute improvement velocity.",
            "sessions_count": len(comparable_sessions),
            "velocity": None,
            "velocity_per_session": None,
            "dimension_deltas": {}
        }

    # Retrieve session score records for the comparable sessions
    session_ids = [s.id for s in comparable_sessions]
    scores = (
        db.query(models.SessionScore)
        .filter(models.SessionScore.session_id.in_(session_ids))
        .all()
    )
    score_by_session = {sc.session_id: sc for sc in scores}

    # Extract score timeline
    first_session = comparable_sessions[0]
    last_session = comparable_sessions[-1]
    first_score = score_by_session.get(first_session.id)
    last_score = score_by_session.get(last_session.id)

    if not first_score or not last_score:
        return {
            "status": "insufficient_data",
            "message": "Score records missing for one or more comparable sessions.",
            "sessions_count": len(comparable_sessions),
            "velocity": None,
            "dimension_deltas": {}
        }

    n_sessions = len(comparable_sessions)
    intervals = n_sessions - 1

    readiness_start = first_score.readiness_score or 0.0
    readiness_end = last_score.readiness_score or 0.0
    readiness_delta = round(readiness_end - readiness_start, 1)
    velocity_per_session = round(readiness_delta / intervals, 2)

    # Dimension-specific deltas
    comm_delta = round((last_score.communication_score or 0.0) - (first_score.communication_score or 0.0), 1)
    tech_delta = round((last_score.technical_score or 0.0) - (first_score.technical_score or 0.0), 1)
    resume_delta = round((last_score.resume_consistency_score or 0.0) - (first_score.resume_consistency_score or 0.0), 1)

    delivery_delta = None
    if first_score.behavioral_score is not None and last_score.behavioral_score is not None:
        delivery_delta = round(last_score.behavioral_score - first_score.behavioral_score, 1)

    direction = "improved" if readiness_delta > 0 else ("declined" if readiness_delta < 0 else "remained stable")
    pts_str = f"{abs(readiness_delta)} points"

    if readiness_delta > 0:
        summary_text = f"Readiness improved by {readiness_delta} points across {n_sessions} comparable sessions ({velocity_per_session:+.1f} pts/session)."
    elif readiness_delta < 0:
        summary_text = f"Readiness changed by {readiness_delta} points across {n_sessions} comparable sessions ({velocity_per_session:+.1f} pts/session)."
    else:
        summary_text = f"Readiness remained stable across {n_sessions} comparable sessions (0.0 pt change)."

    return {
        "status": "computed",
        "comparable_session_ids": session_ids,
        "sessions_count": n_sessions,
        "readiness_delta": readiness_delta,
        "velocity_per_session": velocity_per_session,
        "first_session_score": readiness_start,
        "latest_session_score": readiness_end,
        "dimension_deltas": {
            "communication": comm_delta,
            "technical": tech_delta,
            "delivery": delivery_delta,
            "resume_consistency": resume_delta
        },
        "summary": summary_text,
        "disclaimer": "Observed performance changes across repeated practice sessions. We do not claim features alone cause score changes."
    }

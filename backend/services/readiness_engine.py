import math
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from backend.models import models
from backend.services.comparability_service import filter_comparable_sessions
from backend.services.recurring_weakness_service import get_recurring_weaknesses
from backend.config import READINESS_CONFIDENCE_CONFIG


def calculate_readiness_confidence(
    sessions_count: int,
    scores: List[float],
    delivery_measured_ratio: float = 1.0
) -> str:
    """
    Computes readiness estimation confidence based on data sufficiency and score stability.
    Confidence levels:
    - 'insufficient_data' (< 2 sessions)
    - 'low' (2-3 sessions)
    - 'medium' (4-6 sessions, or >=7 with noisy variance)
    - 'high' (>=7 sessions with low variance and measured delivery)

    No arbitrary black-box percentages.
    """
    if sessions_count < READINESS_CONFIDENCE_CONFIG["min_sessions_for_low"]:
        return "insufficient_data"

    if sessions_count < READINESS_CONFIDENCE_CONFIG["min_sessions_for_medium"]:
        return "low"

    if sessions_count < READINESS_CONFIDENCE_CONFIG["min_sessions_for_high"]:
        return "medium"

    # For >= 7 sessions, check score variance
    if len(scores) >= 2:
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = math.sqrt(variance)
        if std_dev <= READINESS_CONFIDENCE_CONFIG["max_score_variance_for_high"] and delivery_measured_ratio >= 0.5:
            return "high"

    return "medium"


def calculate_readiness_trend(scores: List[float]) -> Tuple[str, str, float]:
    """
    Deterministic trend calculation over a sequence of readiness scores.
    Returns:
    - trend: 'improving' | 'stable' | 'declining' | 'insufficient_data'
    - description: observable explanation
    - slope_per_session: float rate of change
    """
    if len(scores) < 2:
        return "insufficient_data", "Need at least 2 comparable sessions to determine a trend.", 0.0

    n = len(scores)
    # Simple linear delta across intervals
    total_change = scores[-1] - scores[0]
    slope = total_change / (n - 1)
    slope_threshold = READINESS_CONFIDENCE_CONFIG["trend_slope_threshold"]

    if slope >= slope_threshold:
        return "improving", f"Readiness improved by {round(total_change, 1)} points over {n} comparable sessions ({round(slope, 1)} pts/session).", round(slope, 2)
    elif slope <= -slope_threshold:
        return "declining", f"Readiness changed by {round(total_change, 1)} points over {n} comparable sessions ({round(slope, 1)} pts/session).", round(slope, 2)
    else:
        return "stable", f"Readiness remained stable within standard variance ({round(slope, 1)} pts/session average change).", round(slope, 2)


def compute_longitudinal_readiness(
    user_id: int,
    db: Session,
    target_threshold: float = 80.0
) -> Dict[str, Any]:
    """
    Builds candidate longitudinal readiness profile combining session-level performance
    with multi-session longitudinal trajectory.

    Guarantees:
    - Does not overwrite or replace individual session readiness scores.
    - Transparent baseline projection bounded 0-100 (never labeled as 'AI prediction').
    - Data-sufficiency confidence gates.
    - No claim that readiness guarantees interview success.
    """
    all_sessions = (
        db.query(models.InterviewSession)
        .filter(
            models.InterviewSession.user_id == user_id,
            models.InterviewSession.status == "completed"
        )
        .order_by(models.InterviewSession.created_at.asc(), models.InterviewSession.id.asc())
        .all()
    )

    if not all_sessions:
        return {
            "status": "no_data",
            "current_readiness": None,
            "confidence": "insufficient_data",
            "trend": "insufficient_data",
            "message": "No completed interview sessions recorded.",
            "target_threshold": target_threshold,
            "target_gap": None,
            "projection": None,
            "disclaimer": "Readiness scores reflect observable rubric performance in practice sessions and do not guarantee actual interview hiring decisions."
        }

    latest_session = all_sessions[-1]
    comparable_sessions = filter_comparable_sessions(latest_session, all_sessions)

    # Fetch score records
    session_ids = [s.id for s in comparable_sessions]
    scores = (
        db.query(models.SessionScore)
        .filter(models.SessionScore.session_id.in_(session_ids))
        .all()
    )
    score_by_session = {sc.session_id: sc for sc in scores}

    # Extract score values
    readiness_list = []
    comm_list = []
    tech_list = []
    deliv_list = []
    resume_list = []

    for s in comparable_sessions:
        sc = score_by_session.get(s.id)
        if sc and sc.readiness_score is not None:
            readiness_list.append(sc.readiness_score)
            if sc.communication_score is not None:
                comm_list.append(sc.communication_score)
            if sc.technical_score is not None:
                tech_list.append(sc.technical_score)
            if sc.behavioral_score is not None:
                deliv_list.append(sc.behavioral_score)
            if sc.resume_consistency_score is not None:
                resume_list.append(sc.resume_consistency_score)

    if not readiness_list:
        latest_score_rec = db.query(models.SessionScore).filter_by(session_id=latest_session.id).first()
        current_val = latest_score_rec.readiness_score if latest_score_rec else 70.0
        readiness_list = [current_val]

    n_sessions = len(readiness_list)
    delivery_ratio = len(deliv_list) / max(1, n_sessions)

    # Compute smoothed current longitudinal readiness:
    # Weighted average giving slightly higher weight to recent sessions
    if n_sessions == 1:
        current_longitudinal = round(readiness_list[0], 1)
    elif n_sessions <= 3:
        current_longitudinal = round(sum(readiness_list) / n_sessions, 1)
    else:
        # 50% latest 2 sessions, 50% earlier sessions
        recent_avg = sum(readiness_list[-2:]) / 2.0
        earlier_avg = sum(readiness_list[:-2]) / len(readiness_list[:-2])
        current_longitudinal = round((0.6 * recent_avg) + (0.4 * earlier_avg), 1)

    # Strictly bounded 0-100
    current_longitudinal = max(0.0, min(100.0, current_longitudinal))

    # Confidence & Trend
    confidence = calculate_readiness_confidence(n_sessions, readiness_list, delivery_ratio)
    trend, trend_desc, slope = calculate_readiness_trend(readiness_list)

    # Strongest / Weakest dimensions
    dim_averages = {
        "Communication": sum(comm_list) / len(comm_list) if comm_list else 70.0,
        "Technical Depth": sum(tech_list) / len(tech_list) if tech_list else 70.0,
        "Resume Consistency": sum(resume_list) / len(resume_list) if resume_list else 70.0,
    }
    if deliv_list:
        dim_averages["Delivery & Stability"] = sum(deliv_list) / len(deliv_list)

    sorted_dims = sorted(dim_averages.items(), key=lambda x: x[1])
    weakest_dim = sorted_dims[0][0]
    strongest_dim = sorted_dims[-1][0]

    # Target readiness gap
    target_gap = round(target_threshold - current_longitudinal, 1)
    if target_gap <= 0.0:
        target_status = "achieved"
        target_message = f"Target readiness of {target_threshold} achieved (current: {current_longitudinal})."
    else:
        target_status = "in_progress"
        if trend == "improving" and n_sessions >= 3:
            target_message = f"Target readiness {target_threshold} is {target_gap} points away. At current improvement trend, target appears achievable, but historical data is insufficient for an exact date estimate."
        else:
            target_message = f"Target readiness {target_threshold} is {target_gap} points away. Continue targeted practice to close the gap."

    # Baseline projection
    projection = None
    if n_sessions >= 3 and confidence in ("low", "medium", "high") and slope > 0:
        projected_3 = max(0.0, min(100.0, round(current_longitudinal + (slope * 3), 1)))
        projection = {
            "projected_score_in_3_sessions": projected_3,
            "type": "Baseline projection",
            "description": f"Baseline linear projection: ~{projected_3}/100 after 3 additional comparable practice sessions at recent trajectory (+{round(slope, 1)} pts/session). Not a performance guarantee.",
            "is_meaningful": True
        }
    else:
        projection = {
            "projected_score_in_3_sessions": None,
            "type": "Baseline projection",
            "description": "Not enough data or stable trajectory for a meaningful score projection.",
            "is_meaningful": False
        }

    # Recurring risk
    recurring_risks = get_recurring_weaknesses(user_id=user_id, db=db)
    top_risk_text = recurring_risks[0]["root_weakness"] if recurring_risks else "No persistent recurring risk patterns detected."

    return {
        "status": "computed",
        "current_readiness": current_longitudinal,
        "latest_session_readiness": round(readiness_list[-1], 1),
        "comparable_sessions_count": n_sessions,
        "confidence": confidence,
        "confidence_factors": {
            "sessions_count": n_sessions,
            "delivery_measured_ratio": round(delivery_ratio, 2),
            "score_variance": round(math.sqrt(sum((s - (sum(readiness_list)/n_sessions))**2 for s in readiness_list)/n_sessions), 1) if n_sessions >= 2 else 0.0
        },
        "trend": trend,
        "trend_description": trend_desc,
        "slope_per_session": slope,
        "strongest_dimension": strongest_dim,
        "weakest_dimension": weakest_dim,
        "dimension_averages": {k: round(v, 1) for k, v in dim_averages.items()},
        "recurring_risk": top_risk_text,
        "target": {
            "threshold": target_threshold,
            "current": current_longitudinal,
            "gap": target_gap,
            "status": target_status,
            "message": target_message
        },
        "projection": projection,
        "disclaimer": "Readiness scores reflect observable rubric performance in practice sessions and do not guarantee actual interview hiring decisions."
    }


from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models import models
from backend.services.weakness_diagnosis_engine import diagnose_session_weaknesses
from backend.config import MIN_SESSIONS_FOR_RECURRING

SEVERITY_SCORE = {
    "low": 1,
    "moderate": 2,
    "high": 3,
    "critical": 4,
}

SCORE_TO_SEVERITY = {
    1: "low",
    2: "moderate",
    3: "high",
    4: "critical",
}


def _score_to_label(avg_score: float) -> str:
    rounded = max(1, min(4, int(round(avg_score))))
    return SCORE_TO_SEVERITY.get(rounded, "moderate")


def aggregate_user_weaknesses(
    user_id: int,
    db: Session,
    min_sessions: int = MIN_SESSIONS_FOR_RECURRING,
    limit_sessions: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Aggregates weaknesses across completed sessions for a specific user.
    Tracks:
    - first_seen
    - last_seen
    - occurrence_count
    - recurring flag (only True if occurrence_count >= min_sessions)
    - average_severity
    - latest_severity
    - severity_history
    - improvement_trend ('improving', 'stable', 'worsening', 'not_sustained')
    - recommended_action

    Guarantees:
    - A single bad session never marks a weakness as 'recurring'.
    - Fully explainable and unit-testable.
    - Zero psychological or accusatory inferences.
    """
    query = (
        db.query(models.InterviewSession)
        .filter(
            models.InterviewSession.user_id == user_id,
            models.InterviewSession.status == "completed"
        )
        .order_by(models.InterviewSession.created_at.asc(), models.InterviewSession.id.asc())
    )
    if limit_sessions:
        query = query.limit(limit_sessions)
    sessions = query.all()

    if not sessions:
        return []

    # Map session_id -> list of diagnosed weaknesses
    session_weaknesses: List[Dict[str, Any]] = []
    for s in sessions:
        w_list = diagnose_session_weaknesses(s.id, db)
        session_weaknesses.append({
            "session_id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "weaknesses": {w["id"]: w for w in w_list}
        })

    # Collect all unique weakness ids seen across sessions
    all_weakness_ids = set()
    for item in session_weaknesses:
        all_weakness_ids.update(item["weaknesses"].keys())

    aggregated: List[Dict[str, Any]] = []
    total_sessions_count = len(sessions)

    for w_id in sorted(all_weakness_ids):
        occurrences = []
        for idx, item in enumerate(session_weaknesses):
            if w_id in item["weaknesses"]:
                w_obj = item["weaknesses"][w_id]
                occurrences.append({
                    "session_index": idx,
                    "session_id": item["session_id"],
                    "created_at": item["created_at"],
                    "severity": w_obj.get("severity", "moderate"),
                    "details": w_obj
                })

        if not occurrences:
            continue

        occ_count = len(occurrences)
        first_occ = occurrences[0]
        last_occ = occurrences[-1]

        # Calculate severity metrics
        sev_scores = [SEVERITY_SCORE.get(o["severity"], 2) for o in occurrences]
        avg_sev_score = sum(sev_scores) / len(sev_scores)
        avg_sev_label = _score_to_label(avg_sev_score)
        latest_sev_label = last_occ["severity"]

        # Determine trend
        trend = "stable"
        trend_explanation = "Weakness severity is unchanged across observed sessions."

        # Check if weakness was absent in the latest session
        latest_session_id = session_weaknesses[-1]["session_id"]
        is_in_latest_session = w_id in session_weaknesses[-1]["weaknesses"]

        if not is_in_latest_session and occ_count > 0:
            trend = "improving"
            trend_explanation = f"Not detected in latest session #{latest_session_id} (improved)."
        elif occ_count >= 2:
            first_sev = sev_scores[0]
            last_sev = sev_scores[-1]
            if last_sev < first_sev:
                trend = "improving"
                trend_explanation = f"Severity decreased from {occurrences[0]['severity']} to {last_occ['severity']}."
            elif last_sev > first_sev:
                trend = "worsening"
                trend_explanation = f"Severity increased from {occurrences[0]['severity']} to {last_occ['severity']}."
            else:
                # Check for gap (was absent in previous session but reappeared in latest)
                if len(session_weaknesses) >= 3:
                    prev_session_has_it = w_id in session_weaknesses[-2]["weaknesses"]
                    if not prev_session_has_it and is_in_latest_session:
                        trend = "not_sustained"
                        trend_explanation = "Re-emerged in latest session after prior absence (improvement was not sustained)."

        latest_details = last_occ["details"]
        is_recurring = occ_count >= min_sessions

        aggregated.append({
            "weakness_id": w_id,
            "dimension": latest_details.get("dimension", "technical"),
            "root_weakness": latest_details.get("root_weakness", ""),
            "symptom": latest_details.get("symptom", ""),
            "pattern": latest_details.get("pattern", ""),
            "occurrence_count": occ_count,
            "total_sessions_analyzed": total_sessions_count,
            "recurring": is_recurring,
            "first_seen": {
                "session_id": first_occ["session_id"],
                "created_at": first_occ["created_at"]
            },
            "last_seen": {
                "session_id": last_occ["session_id"],
                "created_at": last_occ["created_at"]
            },
            "average_severity": avg_sev_label,
            "latest_severity": latest_sev_label,
            "severity_history": [
                {"session_id": o["session_id"], "severity": o["severity"]}
                for o in occurrences
            ],
            "trend": trend,
            "trend_explanation": trend_explanation,
            "recommended_action": latest_details.get("recommended_action", {})
        })

    # Sort deterministically: recurring first, then highest latest severity, then occurrence count desc
    aggregated.sort(
        key=lambda x: (
            not x["recurring"],
            -SEVERITY_SCORE.get(x["latest_severity"], 0),
            -x["occurrence_count"],
            x["weakness_id"]
        )
    )
    return aggregated


def get_recurring_weaknesses(
    user_id: int,
    db: Session,
    min_sessions: int = MIN_SESSIONS_FOR_RECURRING
) -> List[Dict[str, Any]]:
    """Returns only weaknesses verified as recurring across multiple sessions."""
    all_w = aggregate_user_weaknesses(user_id=user_id, db=db, min_sessions=min_sessions)
    return [w for w in all_w if w["recurring"]]


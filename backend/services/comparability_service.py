from typing import Tuple, List, Optional
from backend.models import models

MIN_ANSWERS_FOR_COMPARABILITY = 2


def normalize_role(role: Optional[str]) -> str:
    """Normalizes role string for comparison."""
    if not role:
        return "software engineer"
    r = role.strip().lower()
    if "backend" in r:
        return "backend engineer"
    if "frontend" in r:
        return "frontend engineer"
    if "fullstack" in r or "full-stack" in r or "full stack" in r:
        return "full-stack engineer"
    if "ml" in r or "ai" in r or "machine learning" in r:
        return "ai / ml engineer"
    return r


def is_comparable(
    session_a: models.InterviewSession,
    session_b: models.InterviewSession
) -> Tuple[bool, str]:
    """
    Evaluates whether two interview sessions are genuinely comparable for longitudinal progress tracking.

    Criteria:
    1. Both sessions must be 'completed'.
    2. Same primary target role/domain.
    3. Same interview mode (e.g. Technical vs Technical, Pressure vs Pressure).
    4. Minimum answered questions count in each session (>= MIN_ANSWERS_FOR_COMPARABILITY).
    5. Difficulty band within 1 level (e.g. easy <-> medium or medium <-> hard, but not easy <-> hard).

    Returns:
        (is_comparable: bool, reason: str)
    """
    if not session_a or not session_b:
        return False, "One or both sessions are missing."

    if session_a.id == session_b.id:
        return True, "Identical session."

    # 1. Completion status check
    if session_a.status != "completed":
        return False, f"Session #{session_a.id} is not completed (status: '{session_a.status}')."
    if session_b.status != "completed":
        return False, f"Session #{session_b.id} is not completed (status: '{session_b.status}')."

    # 2. Target role check
    role_a = normalize_role(session_a.target_role)
    role_b = normalize_role(session_b.target_role)
    if role_a != role_b:
        return False, f"Target roles differ ('{session_a.target_role}' vs '{session_b.target_role}')."

    # 3. Interview mode check
    mode_a = (session_a.mode or "technical").strip().lower()
    mode_b = (session_b.mode or "technical").strip().lower()
    if mode_a != mode_b:
        return False, f"Interview modes differ ('{mode_a}' vs '{mode_b}')."

    # 4. Minimum answers count check
    answers_count_a = len(session_a.answers) if session_a.answers is not None else 0
    answers_count_b = len(session_b.answers) if session_b.answers is not None else 0
    if answers_count_a < MIN_ANSWERS_FOR_COMPARABILITY:
        return False, f"Session #{session_a.id} has only {answers_count_a} answers (minimum {MIN_ANSWERS_FOR_COMPARABILITY} required)."
    if answers_count_b < MIN_ANSWERS_FOR_COMPARABILITY:
        return False, f"Session #{session_b.id} has only {answers_count_b} answers (minimum {MIN_ANSWERS_FOR_COMPARABILITY} required)."

    # 5. Difficulty distance check
    diff_order = {"easy": 1, "medium": 2, "hard": 3}
    d_a = diff_order.get((session_a.difficulty or "medium").strip().lower(), 2)
    d_b = diff_order.get((session_b.difficulty or "medium").strip().lower(), 2)
    if abs(d_a - d_b) > 1:
        return False, f"Difficulty gap too large ('{session_a.difficulty}' vs '{session_b.difficulty}')."

    return True, "Sessions meet role, mode, completion, and difficulty comparability criteria."


def filter_comparable_sessions(
    reference_session: models.InterviewSession,
    all_sessions: List[models.InterviewSession]
) -> List[models.InterviewSession]:
    """Filters a list of sessions returning only those comparable to the reference session."""
    comparable = []
    for s in all_sessions:
        ok, _ = is_comparable(reference_session, s)
        if ok:
            comparable.append(s)
    # Sort chronologically
    comparable.sort(key=lambda s: (s.created_at or 0, s.id))
    return comparable

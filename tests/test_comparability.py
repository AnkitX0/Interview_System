import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.comparability_service import (
    is_comparable,
    normalize_role,
    filter_comparable_sessions
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_session(db, s_id: int, role: str, mode: str, diff: str, status: str = "completed", answer_count: int = 3):
    s = models.InterviewSession(
        id=s_id,
        user_id=1,
        target_role=role,
        mode=mode,
        difficulty=diff,
        status=status
    )
    db.add(s)
    for i in range(answer_count):
        ans = models.InterviewAnswer(session_id=s_id, transcript=f"Answer {i} content")
        db.add(ans)
    db.commit()
    return s


def test_normalize_role():
    assert normalize_role("Senior Backend Engineer") == "backend engineer"
    assert normalize_role("frontend engineer") == "frontend engineer"
    assert normalize_role("Full-Stack Developer") == "full-stack engineer"
    assert normalize_role("Machine Learning Specialist") == "ai / ml engineer"
    assert normalize_role(None) == "software engineer"


def test_identical_sessions_are_comparable(db_session):
    s1 = _make_session(db_session, 1, "Backend Engineer", "technical", "medium")
    ok, reason = is_comparable(s1, s1)
    assert ok is True
    assert "Identical session" in reason


def test_same_mode_and_role_are_comparable(db_session):
    s1 = _make_session(db_session, 2, "Backend Engineer", "technical", "medium")
    s2 = _make_session(db_session, 3, "Backend Engineer", "technical", "hard")
    ok, reason = is_comparable(s1, s2)
    assert ok is True
    assert "meet" in reason.lower()


def test_different_roles_are_not_comparable(db_session):
    s1 = _make_session(db_session, 4, "Backend Engineer", "technical", "medium")
    s2 = _make_session(db_session, 5, "Frontend Engineer", "technical", "medium")
    ok, reason = is_comparable(s1, s2)
    assert ok is False
    assert "Target roles differ" in reason


def test_different_modes_are_not_comparable(db_session):
    s1 = _make_session(db_session, 6, "Backend Engineer", "technical", "medium")
    s2 = _make_session(db_session, 7, "Backend Engineer", "behavioral", "medium")
    ok, reason = is_comparable(s1, s2)
    assert ok is False
    assert "Interview modes differ" in reason


def test_incomplete_sessions_are_not_comparable(db_session):
    s1 = _make_session(db_session, 8, "Backend Engineer", "technical", "medium", status="completed")
    s2 = _make_session(db_session, 9, "Backend Engineer", "technical", "medium", status="in_progress")
    ok, reason = is_comparable(s1, s2)
    assert ok is False
    assert "not completed" in reason


def test_insufficient_answers_are_not_comparable(db_session):
    s1 = _make_session(db_session, 10, "Backend Engineer", "technical", "medium", answer_count=3)
    s2 = _make_session(db_session, 11, "Backend Engineer", "technical", "medium", answer_count=1)
    ok, reason = is_comparable(s1, s2)
    assert ok is False
    assert "minimum 2 required" in reason.lower()


def test_large_difficulty_gap_is_not_comparable(db_session):
    # easy vs hard has gap of 2 levels (>1)
    s1 = _make_session(db_session, 12, "Backend Engineer", "technical", "easy")
    s2 = _make_session(db_session, 13, "Backend Engineer", "technical", "hard")
    ok, reason = is_comparable(s1, s2)
    assert ok is False
    assert "Difficulty gap too large" in reason


def test_filter_comparable_sessions_utility(db_session):
    ref = _make_session(db_session, 20, "Backend Engineer", "technical", "medium")
    s_good = _make_session(db_session, 21, "Backend Engineer", "technical", "medium")
    s_diff_role = _make_session(db_session, 22, "Frontend Engineer", "technical", "medium")
    s_diff_mode = _make_session(db_session, 23, "Backend Engineer", "behavioral", "medium")

    filtered = filter_comparable_sessions(ref, [ref, s_good, s_diff_role, s_diff_mode])
    filtered_ids = [s.id for s in filtered]
    assert 20 in filtered_ids
    assert 21 in filtered_ids
    assert 22 not in filtered_ids
    assert 23 not in filtered_ids


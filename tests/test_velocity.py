import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.velocity_service import calculate_improvement_velocity


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


def _create_scored_session(db, session_id: int, user_id: int, role: str, mode: str, diff: str, readiness: float, comm: float = 70.0, tech: float = 70.0, deliv: float = 75.0, resume: float = 75.0):
    s = models.InterviewSession(
        id=session_id,
        user_id=user_id,
        target_role=role,
        mode=mode,
        difficulty=diff,
        status="completed"
    )
    db.add(s)

    # Add 2 answers for minimum answer check
    a1 = models.InterviewAnswer(session_id=session_id, transcript="Answer 1")
    a2 = models.InterviewAnswer(session_id=session_id, transcript="Answer 2")
    db.add_all([a1, a2])

    sc = models.SessionScore(
        session_id=session_id,
        readiness_score=readiness,
        communication_score=comm,
        technical_score=tech,
        behavioral_score=deliv,
        resume_consistency_score=resume
    )
    db.add(sc)
    db.commit()
    return s


def test_velocity_insufficient_data_with_single_session(db_session):
    u = models.User(id=1, email="solo@test.com", password_hash="h")
    db_session.add(u)
    db_session.commit()

    _create_scored_session(db_session, 10, 1, "Backend Engineer", "technical", "medium", readiness=65.0)

    res = calculate_improvement_velocity(user_id=1, db=db_session)
    assert res["status"] == "insufficient_data"
    assert "Minimum 2 comparable sessions required" in res["message"]
    assert res["velocity_per_session"] is None


def test_velocity_computed_across_four_comparable_sessions(db_session):
    u = models.User(id=2, email="student@test.com", password_hash="h")
    db_session.add(u)
    db_session.commit()

    # 54 -> 61 -> 66 -> 71
    _create_scored_session(db_session, 21, 2, "Backend Engineer", "technical", "medium", readiness=54.0, comm=50.0, tech=55.0)
    _create_scored_session(db_session, 22, 2, "Backend Engineer", "technical", "medium", readiness=61.0, comm=58.0, tech=62.0)
    _create_scored_session(db_session, 23, 2, "Backend Engineer", "technical", "medium", readiness=66.0, comm=63.0, tech=68.0)
    _create_scored_session(db_session, 24, 2, "Backend Engineer", "technical", "medium", readiness=71.0, comm=71.0, tech=72.0)

    res = calculate_improvement_velocity(user_id=2, db=db_session)
    assert res["status"] == "computed"
    assert res["sessions_count"] == 4
    assert res["readiness_delta"] == 17.0
    assert res["velocity_per_session"] == round(17.0 / 3, 2)  # ~5.67
    assert res["dimension_deltas"]["communication"] == 21.0
    assert res["dimension_deltas"]["technical"] == 17.0
    assert "17.0 points across 4 comparable sessions" in res["summary"]
    assert "We do not claim features alone cause score changes" in res["disclaimer"]


def test_velocity_ignores_non_comparable_sessions(db_session):
    u = models.User(id=3, email="mixed@test.com", password_hash="h")
    db_session.add(u)
    db_session.commit()

    # Session 31: Backend technical
    _create_scored_session(db_session, 31, 3, "Backend Engineer", "technical", "medium", readiness=60.0)
    # Session 32: HR behavioral (different mode!)
    _create_scored_session(db_session, 32, 3, "Backend Engineer", "behavioral", "medium", readiness=85.0)
    # Session 33: Frontend technical (different role!)
    _create_scored_session(db_session, 33, 3, "Frontend Engineer", "technical", "medium", readiness=90.0)

    # Reference is latest session (Frontend technical), has only 1 session
    res = calculate_improvement_velocity(user_id=3, db=db_session)
    assert res["status"] == "insufficient_data"
    assert res["sessions_count"] == 1

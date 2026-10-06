import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.readiness_engine import (
    compute_longitudinal_readiness,
    calculate_readiness_confidence,
    calculate_readiness_trend
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


def _add_session(db, s_id: int, user_id: int, readiness: float, comm: float = 70.0, tech: float = 70.0, deliv: float = 75.0):
    s = models.InterviewSession(
        id=s_id,
        user_id=user_id,
        target_role="Backend Engineer",
        mode="technical",
        difficulty="medium",
        status="completed"
    )
    db.add(s)
    a1 = models.InterviewAnswer(session_id=s_id, transcript="Answer 1")
    a2 = models.InterviewAnswer(session_id=s_id, transcript="Answer 2")
    db.add_all([a1, a2])
    sc = models.SessionScore(
        session_id=s_id,
        readiness_score=readiness,
        communication_score=comm,
        technical_score=tech,
        behavioral_score=deliv,
        resume_consistency_score=75.0
    )
    db.add(sc)
    db.commit()
    return s


def test_calculate_readiness_confidence_levels():
    assert calculate_readiness_confidence(1, [60.0]) == "insufficient_data"
    assert calculate_readiness_confidence(2, [60.0, 65.0]) == "low"
    assert calculate_readiness_confidence(5, [60.0, 62.0, 65.0, 68.0, 70.0]) == "medium"
    # 7 stable sessions with measured delivery
    assert calculate_readiness_confidence(7, [70.0, 71.0, 69.0, 70.0, 72.0, 71.0, 70.0], delivery_measured_ratio=1.0) == "high"


def test_calculate_readiness_trend():
    trend, desc, slope = calculate_readiness_trend([54.0, 61.0, 63.0, 67.0, 71.0])
    assert trend == "improving"
    assert slope > 1.5

    trend, desc, slope = calculate_readiness_trend([70.0, 69.0, 71.0, 70.0])
    assert trend == "stable"
    assert abs(slope) < 1.5

    trend, desc, slope = calculate_readiness_trend([80.0, 74.0, 68.0])
    assert trend == "declining"
    assert slope < -1.5


def test_compute_longitudinal_readiness_improving_candidate(db_session):
    u = models.User(id=1, email="improving@test.com", password_hash="h")
    db_session.add(u)
    db_session.commit()

    # 54 -> 61 -> 66 -> 71
    _add_session(db_session, 11, 1, 54.0, comm=50.0, tech=55.0)
    _add_session(db_session, 12, 1, 61.0, comm=58.0, tech=62.0)
    _add_session(db_session, 13, 1, 66.0, comm=63.0, tech=68.0)
    _add_session(db_session, 14, 1, 71.0, comm=72.0, tech=73.0)

    res = compute_longitudinal_readiness(user_id=1, db=db_session, target_threshold=80.0)
    assert res["status"] == "computed"
    assert res["trend"] == "improving"
    assert res["confidence"] in ("medium", "low")
    assert res["target"]["gap"] > 0
    assert res["target"]["status"] == "in_progress"
    assert "target appears achievable" in res["target"]["message"].lower()

    # Projection check
    assert res["projection"]["is_meaningful"] is True
    assert res["projection"]["type"] == "Baseline projection"
    assert "Not a performance guarantee" in res["projection"]["description"]


def test_target_readiness_achieved(db_session):
    u = models.User(id=2, email="ready@test.com", password_hash="h")
    db_session.add(u)
    db_session.commit()

    _add_session(db_session, 21, 2, 82.0)
    _add_session(db_session, 22, 2, 85.0)

    res = compute_longitudinal_readiness(user_id=2, db=db_session, target_threshold=80.0)
    assert res["target"]["status"] == "achieved"
    assert "achieved" in res["target"]["message"].lower()
    assert "guarantee" in res["disclaimer"].lower()

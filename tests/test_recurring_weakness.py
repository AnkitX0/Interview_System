import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.recurring_weakness_service import (
    aggregate_user_weaknesses,
    get_recurring_weaknesses
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


def _create_filler_session(db, session_id: int, user_id: int, filler_count: int, tech_score: float = 75.0):
    s = models.InterviewSession(id=session_id, user_id=user_id, mode="technical", difficulty="medium", status="completed")
    db.add(s)

    a1 = models.InterviewAnswer(session_id=session_id, transcript="Answer one transcript with details.", duration_seconds=30.0)
    a2 = models.InterviewAnswer(session_id=session_id, transcript="Answer two transcript with details.", duration_seconds=30.0)
    db.add_all([a1, a2])
    db.flush()

    v1 = models.VoiceMetrics(answer_id=a1.id, filler_word_count=filler_count, speech_source="speech")
    v2 = models.VoiceMetrics(answer_id=a2.id, filler_word_count=filler_count, speech_source="speech")
    e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=tech_score)
    e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=tech_score)
    db.add_all([v1, v2, e1, e2])
    db.commit()
    return s


def test_single_bad_session_does_not_label_recurring(db_session):
    u = models.User(id=1, email="candidate1@test.com", password_hash="hash")
    db_session.add(u)
    db_session.commit()

    # Session 1: High fillers (6 per answer = 12 total)
    _create_filler_session(db_session, session_id=101, user_id=1, filler_count=6)

    agg = aggregate_user_weaknesses(user_id=1, db=db_session)
    assert len(agg) >= 1
    filler_w = next((w for w in agg if w["weakness_id"] == "comm_excessive_fillers"), None)
    assert filler_w is not None
    assert filler_w["occurrence_count"] == 1
    assert filler_w["recurring"] is False  # NOT recurring from single session

    rec = get_recurring_weaknesses(user_id=1, db=db_session)
    assert len(rec) == 0  # 0 recurring weaknesses


def test_repeated_evidence_labels_weakness_recurring(db_session):
    u = models.User(id=2, email="candidate2@test.com", password_hash="hash")
    db_session.add(u)
    db_session.commit()

    # Session 1 & 2: High fillers
    _create_filler_session(db_session, session_id=201, user_id=2, filler_count=6)
    _create_filler_session(db_session, session_id=202, user_id=2, filler_count=7)

    agg = aggregate_user_weaknesses(user_id=2, db=db_session)
    filler_w = next((w for w in agg if w["weakness_id"] == "comm_excessive_fillers"), None)
    assert filler_w is not None
    assert filler_w["occurrence_count"] == 2
    assert filler_w["recurring"] is True  # Recurring now!
    assert filler_w["first_seen"]["session_id"] == 201
    assert filler_w["last_seen"]["session_id"] == 202

    rec = get_recurring_weaknesses(user_id=2, db=db_session)
    assert len(rec) == 1
    assert rec[0]["weakness_id"] == "comm_excessive_fillers"


def test_improvement_detected_when_weakness_clears_in_subsequent_session(db_session):
    u = models.User(id=3, email="candidate3@test.com", password_hash="hash")
    db_session.add(u)
    db_session.commit()

    # Session 1: High fillers
    _create_filler_session(db_session, session_id=301, user_id=3, filler_count=6)
    # Session 2: Clean speech (0 fillers)
    _create_filler_session(db_session, session_id=302, user_id=3, filler_count=0)

    agg = aggregate_user_weaknesses(user_id=3, db=db_session)
    filler_w = next((w for w in agg if w["weakness_id"] == "comm_excessive_fillers"), None)
    assert filler_w is not None
    assert filler_w["trend"] == "improving"
    assert "improved" in filler_w["trend_explanation"].lower()


def test_unsustained_improvement_reporting(db_session):
    u = models.User(id=4, email="candidate4@test.com", password_hash="hash")
    db_session.add(u)
    db_session.commit()

    # Session 1: High fillers
    _create_filler_session(db_session, session_id=401, user_id=4, filler_count=6)
    # Session 2: Clean speech
    _create_filler_session(db_session, session_id=402, user_id=4, filler_count=0)
    # Session 3: High fillers returns
    _create_filler_session(db_session, session_id=403, user_id=4, filler_count=7)

    agg = aggregate_user_weaknesses(user_id=4, db=db_session)
    filler_w = next((w for w in agg if w["weakness_id"] == "comm_excessive_fillers"), None)
    assert filler_w is not None
    assert filler_w["trend"] == "not_sustained"
    assert "not sustained" in filler_w["trend_explanation"].lower()

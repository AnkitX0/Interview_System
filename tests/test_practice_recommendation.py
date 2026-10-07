import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.practice_recommendation_engine import (
    select_next_practice,
    VALID_PRACTICE_TYPES
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


def _make_candidate_with_weakness(db, user_id: int, weakness_type: str):
    u = models.User(id=user_id, email=f"user{user_id}@test.com", password_hash="hash")
    db.add(u)
    db.commit()

    s = models.InterviewSession(id=user_id * 10, user_id=user_id, status="completed", mode="technical", difficulty="medium")
    db.add(s)

    a1 = models.InterviewAnswer(session_id=s.id, transcript="Sample answer 1", duration_seconds=40.0)
    a2 = models.InterviewAnswer(session_id=s.id, transcript="Sample answer 2", duration_seconds=40.0)
    db.add_all([a1, a2])
    db.commit()

    if weakness_type == "fillers":
        v1 = models.VoiceMetrics(answer_id=a1.id, filler_word_count=8, speech_source="speech")
        v2 = models.VoiceMetrics(answer_id=a2.id, filler_word_count=7, speech_source="speech")
        e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=75.0)
        e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=75.0)
        db.add_all([v1, v2, e1, e2])
    elif weakness_type == "shallow_tech":
        e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=45.0)
        e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=48.0)
        db.add_all([e1, e2])

    db.commit()
    return u, s


def test_select_next_practice_recommends_communication_for_fillers(db_session):
    u, s = _make_candidate_with_weakness(db_session, user_id=1, weakness_type="fillers")

    recs = select_next_practice(user_id=1, db=db_session, source_session_id=s.id)
    assert len(recs) >= 1
    primary = recs[0]
    assert primary["priority"] == 1
    assert primary["practice_type"] == "COMMUNICATION"
    assert primary["practice_type"] in VALID_PRACTICE_TYPES
    assert primary["target_count"] == 5
    assert "filler" in primary["rationale"].lower() or "filler" in primary["weakness"].lower()

    # Verify persisted in database
    db_rec = db_session.query(models.PracticeRecommendation).filter_by(user_id=1, priority=1).first()
    assert db_rec is not None
    assert db_rec.practice_type == "COMMUNICATION"
    assert db_rec.status == "pending"


def test_select_next_practice_recommends_technical_depth_for_low_scores(db_session):
    u, s = _make_candidate_with_weakness(db_session, user_id=2, weakness_type="shallow_tech")

    recs = select_next_practice(user_id=2, db=db_session, source_session_id=s.id)
    assert len(recs) >= 1
    primary = recs[0]
    assert primary["priority"] == 1
    assert primary["practice_type"] == "TECHNICAL_DEPTH"
    assert primary["difficulty"] in ("medium", "hard")
    assert "technical" in primary["dimension"]


def test_recurring_weakness_prioritized_over_single_occurrence(db_session):
    u = models.User(id=3, email="recurring@test.com", password_hash="h")
    db_session.add(u)

    # Session 1: Shallow tech (tech score 50)
    s1 = models.InterviewSession(id=301, user_id=3, status="completed", mode="technical", difficulty="medium")
    db_session.add(s1)
    a1 = models.InterviewAnswer(session_id=301, transcript="Ans 1")
    a2 = models.InterviewAnswer(session_id=301, transcript="Ans 2")
    db_session.add_all([a1, a2])
    db_session.flush()
    e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=48.0)
    e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=49.0)
    db_session.add_all([e1, e2])

    # Session 2: Shallow tech repeated + single filler burst
    s2 = models.InterviewSession(id=302, user_id=3, status="completed", mode="technical", difficulty="medium")
    db_session.add(s2)
    a3 = models.InterviewAnswer(session_id=302, transcript="Ans 3")
    a4 = models.InterviewAnswer(session_id=302, transcript="Ans 4")
    db_session.add_all([a3, a4])
    db_session.flush()
    e3 = models.AnswerEvaluation(answer_id=a3.id, technical_score=45.0)
    e4 = models.AnswerEvaluation(answer_id=a4.id, technical_score=46.0)
    v3 = models.VoiceMetrics(answer_id=a3.id, filler_word_count=5, speech_source="speech")
    v4 = models.VoiceMetrics(answer_id=a4.id, filler_word_count=5, speech_source="speech")
    db_session.add_all([e3, e4, v3, v4])
    db_session.commit()

    recs = select_next_practice(user_id=3, db=db_session, source_session_id=302)
    assert len(recs) >= 1
    # Technical depth has 2 occurrences (recurring) and high severity, should be rank 1
    assert recs[0]["practice_type"] == "TECHNICAL_DEPTH"
    assert recs[0]["decision_metadata"]["recurring"] is True


def test_fallback_practice_when_no_weakness_detected(db_session):
    u = models.User(id=4, email="flawless@test.com", password_hash="h")
    db_session.add(u)
    s = models.InterviewSession(id=401, user_id=4, status="completed", mode="technical", difficulty="hard", target_role="Backend Engineer")
    db_session.add(s)
    a1 = models.InterviewAnswer(session_id=401, transcript="Flawless answer 1")
    a2 = models.InterviewAnswer(session_id=401, transcript="Flawless answer 2")
    db_session.add_all([a1, a2])
    db_session.flush()
    e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=95.0)
    e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=92.0)
    db_session.add_all([e1, e2])
    db_session.commit()

    recs = select_next_practice(user_id=4, db=db_session, source_session_id=401)
    assert len(recs) == 1
    assert recs[0]["practice_type"] == "TRADEOFF_REASONING"
    assert "mastery" in recs[0]["rationale"].lower() or "advanced" in recs[0]["rationale"].lower()


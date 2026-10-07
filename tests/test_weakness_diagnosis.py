import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.weakness_diagnosis_engine import (
    get_performance_dimension_model,
    diagnose_session_weaknesses
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


def test_performance_dimension_model_structure(db_session):
    s = models.InterviewSession(id=1, mode="technical", difficulty="medium")
    sc = models.SessionScore(
        session_id=1,
        communication_score=78.0,
        technical_score=65.0,
        behavioral_score=None,  # camera off
        resume_consistency_score=82.0
    )
    db_session.add_all([s, sc])
    db_session.commit()

    dim_model = get_performance_dimension_model(1, db_session)
    assert "communication" in dim_model
    assert "technical" in dim_model
    assert "delivery" in dim_model
    assert "resume_consistency" in dim_model

    assert dim_model["communication"]["score"] == 78.0
    assert dim_model["communication"]["state"] == "measured"
    assert dim_model["delivery"]["state"] == "not_measured"
    assert dim_model["delivery"]["score"] is None
    assert "recommended_action" in dim_model["technical"]


def test_no_weakness_diagnosed_from_single_noisy_metric(db_session):
    s = models.InterviewSession(id=2, mode="technical", difficulty="medium")
    db_session.add(s)

    # 3 answers, only 1 answer has 5 fillers (below 2-answer or session threshold of 8)
    a1 = models.InterviewAnswer(session_id=2, transcript="I built a distributed service.", duration_seconds=40.0)
    a2 = models.InterviewAnswer(session_id=2, transcript="We used Postgres.", duration_seconds=40.0)
    a3 = models.InterviewAnswer(session_id=2, transcript="Um like basically yeah.", duration_seconds=40.0)
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    v1 = models.VoiceMetrics(answer_id=a1.id, filler_word_count=0, speech_source="speech")
    v2 = models.VoiceMetrics(answer_id=a2.id, filler_word_count=1, speech_source="speech")
    v3 = models.VoiceMetrics(answer_id=a3.id, filler_word_count=5, speech_source="speech")
    db_session.add_all([v1, v2, v3])

    e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=80.0)
    e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=75.0)
    e3 = models.AnswerEvaluation(answer_id=a3.id, technical_score=70.0)
    db_session.add_all([e1, e2, e3])
    db_session.commit()

    weaknesses = diagnose_session_weaknesses(2, db_session)
    # Total fillers = 6 (less than 8 threshold, and only 1 answer had >=5)
    weakness_ids = [w["id"] for w in weaknesses]
    assert "comm_excessive_fillers" not in weakness_ids
    assert "tech_shallow_depth" not in weakness_ids


def test_excessive_fillers_diagnosed_with_sufficient_evidence(db_session):
    s = models.InterviewSession(id=3, mode="technical", difficulty="medium")
    db_session.add(s)

    a1 = models.InterviewAnswer(session_id=3, transcript="Um like uh so basically", duration_seconds=30.0)
    a2 = models.InterviewAnswer(session_id=3, transcript="Um well like you know", duration_seconds=30.0)
    db_session.add_all([a1, a2])
    db_session.commit()

    v1 = models.VoiceMetrics(answer_id=a1.id, filler_word_count=6, speech_source="speech")
    v2 = models.VoiceMetrics(answer_id=a2.id, filler_word_count=7, speech_source="speech")
    e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=75.0)
    e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=72.0)
    db_session.add_all([v1, v2, e1, e2])
    db_session.commit()

    weaknesses = diagnose_session_weaknesses(3, db_session)
    filler_w = next((w for w in weaknesses if w["id"] == "comm_excessive_fillers"), None)
    assert filler_w is not None
    assert filler_w["dimension"] == "communication"
    assert filler_w["severity"] in ("moderate", "high")
    assert "symptom" in filler_w
    assert "pattern" in filler_w
    assert "root_weakness" in filler_w
    assert filler_w["recommended_action"]["practice_type"] == "COMMUNICATION"


def test_followup_degradation_diagnosed_when_probe_score_drops(db_session):
    s = models.InterviewSession(id=4, mode="technical", difficulty="hard")
    db_session.add(s)

    a1 = models.InterviewAnswer(session_id=4, transcript="Initial great architecture answer.", duration_seconds=50.0)
    a2 = models.InterviewAnswer(session_id=4, transcript="I am not sure how the database handles that edge case.", duration_seconds=40.0)
    db_session.add_all([a1, a2])
    db_session.commit()

    e1 = models.AnswerEvaluation(answer_id=a1.id, technical_score=85.0)
    e2 = models.AnswerEvaluation(answer_id=a2.id, technical_score=60.0)  # drop of 25 pts >= 15 pts
    db_session.add_all([e1, e2])
    db_session.commit()

    weaknesses = diagnose_session_weaknesses(4, db_session)
    followup_w = next((w for w in weaknesses if w["id"] == "tech_followup_defense"), None)
    assert followup_w is not None
    assert followup_w["dimension"] == "technical"
    assert "85.0 -> 60.0" in str(followup_w["evidence"])
    assert followup_w["recommended_action"]["practice_type"] == "FOLLOWUP_DEFENSE"


def test_banned_psychological_words_absence_in_diagnosis(db_session):
    s = models.InterviewSession(id=5, mode="pressure", difficulty="hard")
    db_session.add(s)

    a1 = models.InterviewAnswer(session_id=5, transcript="Struggled response.", duration_seconds=45.0)
    db_session.add(a1)
    db_session.commit()

    e1 = models.AnswerEvaluation(
        answer_id=a1.id,
        technical_score=40.0,
        verification_risk_level="elevated",
        verification_risk_evidence=["Ownership vagueness"]
    )
    v1 = models.VoiceMetrics(answer_id=a1.id, filler_word_count=12, speech_source="speech")
    db_session.add_all([e1, v1])
    db_session.commit()

    weaknesses = diagnose_session_weaknesses(5, db_session)
    for w in weaknesses:
        full_text = f"{w['symptom']} {w['pattern']} {w['root_weakness']} {w['explanation']}".lower()
        for banned in ["nervous", "lie", "bluff", "fake", "stress spike", "emotion", "posture check"]:
            assert banned not in full_text


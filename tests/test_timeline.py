import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import models
from backend.services.timeline_service import generate_session_timeline, format_seconds_to_mmss, build_time_range


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


def test_timeline_format_helpers():
    assert format_seconds_to_mmss(0) == "00:00"
    assert format_seconds_to_mmss(75) == "01:15"
    assert format_seconds_to_mmss(360) == "06:00"
    assert build_time_range(10, 70) == "00:10 - 01:10"


def test_empty_session_returns_empty_timeline(db_session):
    s = models.InterviewSession(id=1, mode="technical", difficulty="medium")
    db_session.add(s)
    db_session.commit()

    events = generate_session_timeline(1, db_session)
    assert events == []


def test_deterministic_identical_timeline(db_session):
    s = models.InterviewSession(id=1, mode="technical", difficulty="medium")
    db_session.add(s)

    q1 = models.InterviewQuestion(
        session_id=1,
        sequence_order=1,
        question_text="Explain database indexing in PostgreSQL.",
        question_type="technical",
        difficulty="medium"
    )
    db_session.add(q1)

    a1 = models.InterviewAnswer(
        session_id=1,
        question_id=1,
        question_text="Explain database indexing in PostgreSQL.",
        transcript="PostgreSQL uses B-tree indexes by default for balanced search times.",
        duration_seconds=40.0
    )
    db_session.add(a1)
    db_session.commit()

    ev1 = models.AnswerEvaluation(
        answer_id=a1.id,
        technical_score=88.0,
        overall_score=85.0
    )
    db_session.add(ev1)
    db_session.commit()

    run1 = generate_session_timeline(1, db_session)
    run2 = generate_session_timeline(1, db_session)

    assert len(run1) > 0
    assert run1 == run2

    event_types = [e["event_type"] for e in run1]
    assert "question_started" in event_types
    assert "answer_completed" in event_types
    assert "answer_score_change" in event_types  # high technical score


def test_text_only_session_generates_no_audio_events(db_session):
    s = models.InterviewSession(id=2, mode="technical", difficulty="hard")
    db_session.add(s)

    a = models.InterviewAnswer(
        session_id=2,
        question_id=10,
        question_text="Describe distributed consensus.",
        transcript="Raft uses leader election and log replication.",
        duration_seconds=50.0
    )
    db_session.add(a)
    db_session.commit()

    # VoiceMetrics marked as typed with None cadence
    vm = models.VoiceMetrics(
        answer_id=a.id,
        words_per_minute=None,
        filler_word_count=None,
        longest_pause=None,
        speech_source="typed"
    )
    db_session.add(vm)
    db_session.commit()

    events = generate_session_timeline(2, db_session)
    audio_event_types = {"speaking_speed_change", "filler_spike", "long_pause"}
    for e in events:
        assert e["event_type"] not in audio_event_types


def test_camera_off_session_generates_no_visual_events(db_session):
    s = models.InterviewSession(id=3, mode="technical", difficulty="easy")
    db_session.add(s)

    a = models.InterviewAnswer(
        session_id=3,
        question_id=11,
        question_text="What is a hash table?",
        transcript="A hash table stores key value pairs using hash functions.",
        duration_seconds=30.0
    )
    db_session.add(a)
    db_session.commit()

    # No AnswerVisualMetrics recorded (camera off)
    events = generate_session_timeline(3, db_session)
    visual_event_types = {"visual_quality_drop"}
    for e in events:
        assert e["event_type"] not in visual_event_types
        assert e["dimension"] != "delivery"


def test_spoken_and_visual_metrics_generate_traceable_events(db_session):
    s = models.InterviewSession(id=4, mode="pressure", difficulty="hard")
    db_session.add(s)

    d1 = models.InterviewDecision(
        session_id=4,
        turn=1,
        decision="TRIGGER_CHALLENGE",
        reason="Challenged 10k RPS claim metric."
    )
    db_session.add(d1)

    a = models.InterviewAnswer(
        session_id=4,
        question_id=12,
        question_text="How did you scale the caching cluster?",
        transcript="Um so basically like we like scaled it um rapidly.",
        duration_seconds=45.0
    )
    db_session.add(a)
    db_session.commit()

    vm = models.VoiceMetrics(
        answer_id=a.id,
        words_per_minute=175.0,  # fast cadence
        filler_word_count=6,     # high fillers
        longest_pause=4.2,       # long pause
        speech_source="speech"
    )
    vis = models.AnswerVisualMetrics(
        answer_id=a.id,
        face_visibility_ratio=0.45,  # low visibility (<0.60)
        frames_sampled=60
    )
    ev = models.AnswerEvaluation(
        answer_id=a.id,
        technical_score=48.0,
        verification_risk_level="elevated",
        verification_risk_evidence=["Ownership vagueness", "Missing specific parameters"]
    )
    db_session.add_all([vm, vis, ev])
    db_session.commit()

    events = generate_session_timeline(4, db_session)
    event_types = [e["event_type"] for e in events]

    assert "question_started" in event_types
    assert "pressure_challenge" in event_types
    assert "speaking_speed_change" in event_types
    assert "filler_spike" in event_types
    assert "long_pause" in event_types
    assert "visual_quality_drop" in event_types
    assert "verification_risk_change" in event_types
    assert "answer_score_change" in event_types
    assert "answer_completed" in event_types

    # Ensure no prohibited psychological words
    for e in events:
        desc = (e["title"] + " " + e["description"]).lower()
        for banned in ["nervous", "lie", "bluff", "fake", "stress spike", "emotion", "posture check"]:
            assert banned not in desc

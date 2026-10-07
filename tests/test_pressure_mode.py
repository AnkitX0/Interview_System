import re
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import backend.models as models
from backend.config import PRESSURE_MODE_CONFIG
from backend.services.adaptive_engine import decide_next_question
from backend.services.scoring_engine import evaluate_rubric_for_answer


BANNED_CHALLENGE_WORDS = [
    r"\bstupid\b",
    r"\bobviously\b",
    r"\bwrong answer\b",
    r"\bincompetent\b",
    r"\bclueless\b",
    r"\bbluff\b",
    r"\blie\b",
    r"\bfake\b",
    r"\bidiot\b",
    r"\brubbish\b",
]


def test_pressure_mode_safety_lint():
    """Ensure all challenge templates adhere to professional, calm technical inquiry with no hostile phrasing."""
    templates_dict = PRESSURE_MODE_CONFIG.get("challenge_templates", {})
    assert len(templates_dict) > 0, "Challenge templates must not be empty"

    for category, template_list in templates_dict.items():
        assert len(template_list) >= 2, f"Category {category} should have multiple variations"
        for tpl in template_list:
            for pattern in BANNED_CHALLENGE_WORDS:
                match = re.search(pattern, tpl, re.IGNORECASE)
                assert match is None, f"Template '{tpl}' in '{category}' contained banned hostile word: {pattern}"


def test_pressure_mode_challenge_trigger_numeric_validation(db_session: Session):
    """Answers containing quantitative metrics trigger a numeric validation challenge."""
    user = models.User(email="pressure_num@test.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = models.InterviewSession(
        user_id=user.id,
        mode="pressure",
        difficulty="medium",
        target_role="Backend Engineer",
        current_question_index=1,
    )
    db_session.add(session)
    db_session.commit()

    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text="How did you improve query latency in your service?",
        question_type="bank",
        difficulty="medium",
        source="bank",
    )
    db_session.add(q1)

    a1 = models.InterviewAnswer(
        session_id=session.id,
        question_id=1,
        question_text=q1.question_text,
        transcript="We tuned PostgreSQL indices and reduced p99 latency by 45% down to 12ms under 5000 rps.",
    )
    db_session.add(a1)
    db_session.commit()

    decision = decide_next_question(
        session=session,
        answers=[a1],
        evaluations=[],
        claims=[],
        questions_asked=[q1],
        db=db_session,
    )
    assert decision.decision == "TRIGGER_CHALLENGE"
    assert decision.question_type == "challenge"
    assert decision.inputs.get("challenge_category") == "numeric_validation"
    assert decision.time_limit_seconds == 45


def test_pressure_mode_challenge_trigger_counterexample(db_session: Session):
    """Answers asserting an architectural design decision trigger a counterexample/failure challenge."""
    user = models.User(email="pressure_arch@test.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = models.InterviewSession(
        user_id=user.id,
        mode="pressure",
        difficulty="medium",
        target_role="Backend Engineer",
        current_question_index=1,
    )
    db_session.add(session)
    db_session.commit()

    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text="Describe how you handled service communication.",
        question_type="bank",
        difficulty="medium",
        source="bank",
    )
    db_session.add(q1)

    a1 = models.InterviewAnswer(
        session_id=session.id,
        question_id=1,
        question_text=q1.question_text,
        transcript="I chose a microservices pattern with asynchronous messaging using Kafka.",
    )
    db_session.add(a1)
    db_session.commit()

    decision = decide_next_question(
        session=session,
        answers=[a1],
        evaluations=[],
        claims=[],
        questions_asked=[q1],
        db=db_session,
    )
    assert decision.decision == "TRIGGER_CHALLENGE"
    assert decision.question_type == "challenge"
    assert decision.inputs.get("challenge_category") == "counterexample_failure"
    assert decision.time_limit_seconds == 45


def test_pressure_mode_challenge_caps_and_no_consecutive(db_session: Session):
    """Ensure challenges never occur twice in a row and respect max_challenges_per_session."""
    user = models.User(email="pressure_caps@test.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = models.InterviewSession(
        user_id=user.id,
        mode="pressure",
        difficulty="medium",
        target_role="Backend Engineer",
        current_question_index=2,
    )
    db_session.add(session)
    db_session.commit()

    # Previous question was already a challenge
    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text="Initial question?",
        question_type="bank",
        difficulty="medium",
        source="bank",
    )
    q2 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=2,
        question_text="Challenge question: How was this measured?",
        question_type="challenge",
        difficulty="hard",
        source="pressure",
    )
    db_session.add_all([q1, q2])

    a2 = models.InterviewAnswer(
        session_id=session.id,
        question_id=2,
        question_text=q2.question_text,
        transcript="We reduced memory by 30% through profile-guided memory pool allocation.",
    )
    db_session.add(a2)
    db_session.commit()

    decision = decide_next_question(
        session=session,
        answers=[a2],
        evaluations=[],
        claims=[],
        questions_asked=[q1, q2],
        db=db_session,
    )
    # Even though a2 contains numeric claim, last_was_challenge is true, so challenge must not trigger consecutively
    assert decision.decision != "TRIGGER_CHALLENGE"
    assert decision.question_type != "challenge"


def test_rubric_invariance_between_modes():
    """The scoring engine rubric generates identical scores for the same text in pressure vs practice."""
    answer_text = (
        "In our distributed payments system, we observed significant lock contention during high traffic. "
        "Situation: database deadlocks occurred on merchant ledger balances. "
        "Task: I led the redesign of the balance update concurrency model. "
        "Action: I implemented optimistic concurrency control with Redis-backed lease tokens and exponential backoff retry. "
        "Result: This eliminated database deadlocks completely and reduced transaction abort rates from 8% down to 0.02%."
    )

    scores_normal = evaluate_rubric_for_answer(answer_text, question_text="Tell me about a technical challenge.", category="Technical")
    scores_pressure = evaluate_rubric_for_answer(answer_text, question_text="Tell me about a technical challenge.", category="Technical")

    assert scores_normal["overall_score"] == scores_pressure["overall_score"]
    assert scores_normal["structure_score"] == scores_pressure["structure_score"]
    assert scores_normal["technical_score"] == scores_pressure["technical_score"]
    assert scores_normal["reasoning_score"] == scores_pressure["reasoning_score"]
    assert scores_normal["star_score"] == scores_pressure["star_score"]


def test_api_switch_mode_and_time_limits(client: TestClient, db_session: Session):
    """Test start in pressure mode (45s), switch-mode API (relaxes to 90s), and decision logging."""
    start_resp = client.post(
        "/interview/start",
        json={"mode": "pressure", "difficulty": "hard", "target_role": "Backend Engineer", "question_count": 3},
    )
    assert start_resp.status_code == 200
    data = start_resp.json()
    session_id = data["session_id"]
    questions = data["questions"]
    assert len(questions) > 0
    assert questions[0]["time_limit_seconds"] == 45

    # Call switch-mode endpoint
    switch_resp = client.post(f"/interview/{session_id}/switch-mode")
    assert switch_resp.status_code == 200
    switch_data = switch_resp.json()
    assert switch_data["mode"] == "technical"
    assert switch_data["time_limit_seconds"] == 90

    # Verify decision logged in DB
    decisions = db_session.query(models.InterviewDecision).filter_by(session_id=session_id).all()
    switch_decisions = [d for d in decisions if d.decision == "SWITCH_TO_PRACTICE"]
    assert len(switch_decisions) == 1
    assert "Safe Pressure Mode to Practice Mode" in switch_decisions[0].reason

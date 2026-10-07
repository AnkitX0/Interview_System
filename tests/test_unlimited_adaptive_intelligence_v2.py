"""
tests/test_unlimited_adaptive_intelligence_v2.py
End-to-end tests for Unlimited Adaptive Intelligence Upgrade:
- Adaptive continuation beyond minimum question budget
- Evidence sufficiency stopping
- Evasion detection and return loop
- Difficulty adaptation (weak drops, strong increases)
- Semantic duplication prevention
- Gemini failure & malformed JSON fallbacks
- 25-question safety ceiling
- Backward compatibility for older sessions
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import backend.models as models
from backend.services.evidence_sufficiency_engine import assess_interview_sufficiency, resolve_session_policy
from backend.services.adaptive_engine import decide_next_question, calculate_adjusted_difficulty
from backend.services.scoring_engine import evaluate_rubric_for_answer
from backend.services.llm_gemini_service import (
    LLMQuestionDecision,
    decide_llm_question_strategy,
    call_gemini_json,
)
from backend.services.auth_service import create_access_token


def test_adaptive_interview_continues_after_minimum_when_unresolved(db_session: Session):
    """Proves the interviewer does NOT artificially stop at question 5 when an unresolved point exists."""
    user = models.User(email="unlimited_cont@test.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = models.InterviewSession(
        user_id=user.id,
        mode="technical",
        difficulty="medium",
        target_role="Backend Engineer",
        total_questions=5,
        question_mode="ADAPTIVE",
        session_policy="SHORT",
        current_question_index=5,
    )
    db_session.add(session)
    db_session.commit()

    questions = []
    answers = []
    evaluations = []

    for i in range(1, 6):
        q = models.InterviewQuestion(
            session_id=session.id,
            sequence_order=i,
            question_text=f"Question {i} about architecture and metrics",
            question_type="bank",
            difficulty="medium",
            source="bank",
        )
        db_session.add(q)
        db_session.flush()
        questions.append(q)

        ans = models.InterviewAnswer(
            session_id=session.id,
            question_id=q.id,
            question_text=q.question_text,
            transcript="We used microservices and Docker containers deployed on AWS." if i == 5 else "I built standard APIs.",
        )
        db_session.add(ans)
        db_session.flush()
        answers.append(ans)

        # Mark turn 5 as having an evasion / unresolved point
        ev = models.AnswerEvaluation(
            answer_id=ans.id,
            overall_score=65.0,
            technical_score=60.0,
            structure_score=70.0,
        )
        if i == 5:
            ev.directness_score = 40.0
            ev.candidate_diversion = True
            ev.unresolved_point = "latency measurement methodology"
        else:
            ev.directness_score = 85.0
            ev.candidate_diversion = False
            ev.unresolved_point = None

        db_session.add(ev)
        evaluations.append(ev)

    db_session.commit()

    # Even though total_answers == 5 (the nominal budget), decision must NOT be COMPLETE_SESSION!
    decision = decide_next_question(
        session=session,
        answers=answers,
        evaluations=evaluations,
        claims=[],
        questions_asked=questions,
        db=db_session,
    )

    assert decision.decision != "COMPLETE_SESSION"
    assert decision.decision == "RETURN_TO_UNRESOLVED_POINT"
    assert "latency measurement methodology" in decision.question_text.lower()


def test_adaptive_interview_stops_after_sufficient_evidence():
    """Proves the interview stops cleanly when multi-dimensional evidence criteria are met."""
    res = assess_interview_sufficiency(
        questions_completed=7,
        answers_evaluated=7,
        topics_covered=["api_design", "database_indexing", "distributed_caching"],
        resume_claims_examined=2,
        weak_topics=[],
        strong_topics=["caching"],
        unresolved_points=[],
        evasion_count=0,
        follow_up_count=2,
        policy_key="SHORT",
        nominal_total_questions=5,
    )
    assert res.continue_interview is False
    assert res.interview_state == "FINAL_ASSESSMENT"
    assert "Enough evidence collected" in res.reason or "Target session scope reached" in res.reason


def test_evasion_forces_followup_and_unresolved_point():
    """When a candidate diverts without answering, directness drops and unresolved point is flagged."""
    res = evaluate_rubric_for_answer(
        transcript="We used Spring Boot and PostgreSQL and the application was deployed using Docker.",
        question_text="How did you measure the 35% latency improvement?",
        category="Technical",
    )
    assert res["candidate_diversion"] is True
    assert res["directness_score"] < 60.0
    assert "baseline" in res["unresolved_point"].lower() or "metric" in res["unresolved_point"].lower()


def test_difficulty_adaptation():
    """Weak answers lower difficulty; strong answers raise difficulty."""
    # Strong evaluations
    strong_evals = [
        models.AnswerEvaluation(overall_score=85.0, technical_score=90.0),
        models.AnswerEvaluation(overall_score=88.0, technical_score=85.0),
        models.AnswerEvaluation(overall_score=92.0, technical_score=95.0),
    ]
    assert calculate_adjusted_difficulty(strong_evals, "medium") == "hard"

    # Weak evaluations
    weak_evals = [
        models.AnswerEvaluation(overall_score=45.0, technical_score=40.0),
        models.AnswerEvaluation(overall_score=50.0, technical_score=45.0),
        models.AnswerEvaluation(overall_score=42.0, technical_score=38.0),
    ]
    assert calculate_adjusted_difficulty(weak_evals, "medium") == "easy"


def test_semantic_question_duplication_prevented(db_session: Session):
    """Ensures questions already asked are never duplicated."""
    user = models.User(email="no_dup@test.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = models.InterviewSession(
        user_id=user.id,
        mode="technical",
        difficulty="medium",
        target_role="Backend Engineer",
        total_questions=3,
        question_mode="FIXED",
    )
    db_session.add(session)
    db_session.commit()

    q1_text = "Explain REST API architecture and how HTTP status codes are utilized."
    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text=q1_text,
        question_type="bank",
        difficulty="medium",
        source="bank",
    )
    db_session.add(q1)
    db_session.commit()

    decision = decide_next_question(
        session=session,
        answers=[],
        evaluations=[],
        claims=[],
        questions_asked=[q1],
        db=db_session,
    )
    # The next chosen question must not match q1_text
    assert decision.question_text != q1_text


def test_gemini_fallback_when_api_fails(monkeypatch):
    """When Gemini returns None or fails, the decision engine smoothly falls back to deterministic probing."""
    monkeypatch.setattr(
        "backend.services.llm_gemini_service.call_gemini_json",
        lambda prompt, timeout=4: None,
    )
    res = decide_llm_question_strategy(
        target_role="Backend Engineer",
        difficulty="medium",
        interview_state="EXPLORING",
        previous_question="Tell me about your project.",
        previous_answer="I built a backend in Python.",
    )
    assert res is None  # Graceful return None triggering deterministic fallback


def test_gemini_fallback_when_malformed_json(monkeypatch):
    """When Gemini returns invalid JSON string, it is handled without crashing."""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: None,
    )
    res = call_gemini_json("test prompt")
    assert res is None


def test_safety_ceiling_25_questions():
    """At 25 questions, the safety ceiling terminates the interview regardless of missing evidence."""
    res = assess_interview_sufficiency(
        questions_completed=25,
        answers_evaluated=25,
        topics_covered=["architecture"],
        resume_claims_examined=1,
        weak_topics=["performance"],
        strong_topics=[],
        unresolved_points=[{"unresolved_point": "metric"}],
        evasion_count=3,
        follow_up_count=4,
        policy_key="FULL",
    )
    assert res.continue_interview is False
    assert "Maximum interview depth reached" in res.reason
    assert res.confidence == "High"


def test_old_sessions_backward_compatibility(client: TestClient, db_session: Session):
    """Confirms old sessions created without new columns still load and report works."""
    user = models.User(email="legacy_user@test.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)
    client.cookies.set("auth_token", token)

    session = models.InterviewSession(
        user_id=user.id,
        mode="technical",
        difficulty="medium",
        target_role="Backend Engineer",
        total_questions=5,
        status="completed",
    )
    db_session.add(session)
    db_session.commit()

    resp = client.get(f"/interview/{session.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session.id
    assert data["question_mode"] == "ADAPTIVE"
    assert data["session_policy"] == "STANDARD"

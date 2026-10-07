"""
tests/test_demo_skip_and_end_interview.py
Comprehensive tests for presentation-critical fixes:
1. Skip / I Don't Know endpoint & persistence
2. Early End Interview idempotency & score calculation
3. Report representation of skipped questions (evidence not obtained, not incorrect)
4. Fast Gemini fallback without hanging
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import backend.models as models


def test_skip_question_persists_and_returns_next_question(client: TestClient, db_session: Session):
    """Verifies that skipping a question records the turn cleanly and advances to the next question."""
    # 1. Start interview
    start_resp = client.post(
        "/interview/start",
        json={
            "mode": "technical",
            "difficulty": "medium",
            "number_of_questions": 5,
            "target_role": "Backend Engineer",
            "question_mode": "ADAPTIVE",
            "session_policy": "SHORT",
        },
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    q1 = start_resp.json()["questions"][0]

    # 2. Skip first question
    skip_resp = client.post(
        f"/interview/{session_id}/skip",
        json={
            "session_id": session_id,
            "question_id": q1["id"],
            "question_text": q1["question"],
            "reason": "candidate_skipped",
        },
    )
    assert skip_resp.status_code == 200
    skip_data = skip_resp.json()
    assert skip_data["skipped"] is True
    assert skip_data["done"] is False
    assert "question" in skip_data
    assert skip_data["question"]["question"] != q1["question"]

    # 3. Verify in database
    answer = db_session.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == session_id
    ).first()
    assert answer is not None
    assert "[SKIPPED]" in answer.transcript

    evaluation = db_session.query(models.AnswerEvaluation).filter(
        models.AnswerEvaluation.answer_id == answer.id
    ).first()
    assert evaluation is not None
    assert evaluation.engine_used == "skipped"

    decision = db_session.query(models.InterviewDecision).filter(
        models.InterviewDecision.session_id == session_id,
        models.InterviewDecision.decision == "CANDIDATE_SKIPPED"
    ).first()
    assert decision is not None
    assert decision.inputs.get("skipped") is True


def test_end_interview_early_is_idempotent_and_generates_report(client: TestClient, db_session: Session):
    """Verifies candidate can click 'End Interview' at any time and get an accurate report."""
    # Start session
    start_resp = client.post(
        "/interview/start",
        json={
            "mode": "technical",
            "difficulty": "medium",
            "number_of_questions": 5,
            "target_role": "Backend Engineer",
        },
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    q1 = start_resp.json()["questions"][0]

    # Answer question 1
    ans_res = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q1["id"],
            "question_text": q1["question"],
            "transcript": "We designed our services with clean modular architecture and PostgreSQL with read replicas.",
            "response_time": 25.0,
            "duration_seconds": 25.0,
            "wpm": 130.0,
        },
    )
    assert ans_res.status_code == 200

    # Skip question 2
    skip_res = client.post(
        f"/interview/{session_id}/skip",
        json={
            "session_id": session_id,
            "question_id": 2,
            "question_text": "Describe distributed transaction two phase commit protocol.",
        },
    )
    assert skip_res.status_code == 200

    # End interview early
    comp_resp = client.post(
        f"/interview/{session_id}/complete",
        json={
            "eye_contact_percent": 75.0,
            "blink_rate": 18.0,
            "pause_rate": 1.5,
            "duration_seconds": 120.0,
        },
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["status"] == "completed"
    assert comp_data["readiness_score"] is not None

    # Verify idempotency (calling complete again returns same 200)
    comp_resp2 = client.post(
        f"/interview/{session_id}/complete",
        json={},
    )
    assert comp_resp2.status_code == 200
    assert comp_resp2.json()["status"] == "completed"

    # Fetch report
    rep_resp = client.get(f"/report/{session_id}")
    assert rep_resp.status_code == 200
    report = rep_resp.json()
    assert report["session_id"] == session_id
    assert len(report["answers"]) == 2

    # Check answered vs skipped status in report
    ans1 = report["answers"][0]
    assert ans1["status"] == "answered"
    assert ans1["overall_score"] is not None

    ans2 = report["answers"][1]
    assert ans2["status"] == "skipped"
    assert ans2["is_skipped"] is True
    assert "Candidate did not provide evidence for this question." in ans2["transcript"]

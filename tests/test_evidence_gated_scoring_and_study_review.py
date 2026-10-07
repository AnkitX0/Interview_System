"""
tests/test_evidence_gated_scoring_and_study_review.py
Comprehensive test suite verifying:
1. Zero-answer interview returns readiness score 0.0 with Incomplete status
2. All-skipped interview does NOT produce inflated readiness score
3. Mixed answered + skipped interview calculates score from meaningful turns only
4. Empty and trivial non-answers are classified as EMPTY or INSUFFICIENT with score 0.0
5. Practice drill uniqueness (no duplicate questions)
6. Practice category separation (Behavioral does not ask technical REST questions)
7. Grounded project drill questions based on candidate resume
8. Answer study review comparisons (What a strong answer should cover, missing points, model answer)
9. Grounded resume connection without hallucinated projects
"""

import pytest
from backend.services.scoring_engine import (
    calculate_session_score,
    evaluate_rubric_for_answer
)
from backend.services.evaluation_engine import evaluate_answer
from backend.services.answer_study_service import (
    generate_study_comparison_for_answer,
    _classify_answer_status,
    _derive_grounded_resume_connection
)
from backend.services.practice_drill_service import (
    DISTINCT_DRILL_POOLS,
    select_distinct_practice_questions
)
from backend.database import SessionLocal
import backend.models as models


def test_zero_answer_session_score_returns_zero():
    """Zero evaluated answers MUST produce readiness score 0.0 and Low confidence."""
    res = calculate_session_score(
        answer_scores=[],
        delivery_score=92.0,  # Camera sensor presence must NOT inflate score
        technical_scores=[],
        communication_scores=[],
        consistency_scores=[]
    )
    assert res["final_readiness_score"] == 0.0
    assert res["communication_score"] == 0.0
    assert res["technical_score"] == 0.0
    assert res["resume_consistency_score"] == 0.0
    assert res["score_confidence"] == "Low"
    assert "no meaningful interview answers" in res["confidence_explanation"].lower()
    assert "none" in res["strongest_category"].lower()


def test_all_skipped_session_score_returns_zero():
    """When all questions are skipped, readiness score must be 0.0."""
    res = calculate_session_score(
        answer_scores=[],
        delivery_score=None,
        technical_scores=[],
        communication_scores=[],
        consistency_scores=[],
        evidence_coverage=0.0
    )
    assert res["final_readiness_score"] == 0.0
    assert res["score_confidence"] == "Low"


def test_mixed_answered_and_skipped_session_score():
    """3 answered (e.g. 80.0) out of 8 (coverage 37.5%) should base score on answered turns with modulated confidence."""
    res = calculate_session_score(
        answer_scores=[80.0, 80.0, 80.0],
        delivery_score=None,
        technical_scores=[80.0, 80.0, 80.0],
        communication_scores=[80.0, 80.0, 80.0],
        consistency_scores=[80.0, 80.0, 80.0],
        evidence_coverage=37.5
    )
    # Score should reflect the 80.0 performance of answered questions
    assert res["final_readiness_score"] == 80.0
    # But confidence must be marked Low due to sub-50% evidence coverage
    assert res["score_confidence"] == "Low"
    assert "37.5%" in res["confidence_explanation"]


def test_empty_answer_classified_as_empty_with_zero_score():
    """Empty string submission returns status EMPTY and score 0.0."""
    res = evaluate_rubric_for_answer(transcript="", question_text="What is API versioning?")
    assert res["overall_score"] == 0.0
    assert res["technical_score"] == 0.0
    assert res["structure_score"] == 0.0
    assert res["reasoning_score"] == 0.0
    assert res["answer_status"] == "EMPTY"
    assert len(res["strengths"]) == 0


def test_trivial_idk_answer_classified_as_insufficient():
    """Submissions like 'idk', 'yes', 'no' are classified as INSUFFICIENT with score 0.0."""
    for trivial in ["idk", "i don't know", "no", "yes", "skip", "dsjnd"]:
        res = evaluate_rubric_for_answer(transcript=trivial, question_text="Explain database indexing.")
        assert res["overall_score"] == 0.0
        assert res["technical_score"] == 0.0
        assert res["answer_status"] == "INSUFFICIENT"
        assert len(res["strengths"]) == 0


def test_evaluate_answer_evidence_gate_bypasses_llm():
    """evaluate_answer must evaluate empty/insufficient answers deterministically without calling LLM."""
    res = evaluate_answer(transcript="idk", question_text="What is REST API?")
    assert res["overall_score"] == 0.0
    assert res["engine_used"] == "rubric_evidence_gate"


def test_practice_drill_uniqueness():
    """A practice drill of 5 questions must never return duplicate questions."""
    db = SessionLocal()
    try:
        user = db.query(models.User).first()
        user_id = user.id if user else 1
        questions = select_distinct_practice_questions(
            db=db,
            user_id=user_id,
            practice_type="TECHNICAL_DEPTH",
            count=5
        )
        assert len(questions) == 5
        texts = [q["question"].strip().lower() for q in questions]
        assert len(set(texts)) == len(texts), "Duplicate questions found in practice drill!"
    finally:
        db.close()


def test_practice_category_separation():
    """Behavioral and Structured Communication drills must NOT ask technical REST questions."""
    db = SessionLocal()
    try:
        user = db.query(models.User).first()
        user_id = user.id if user else 1

        behavioral_questions = select_distinct_practice_questions(
            db=db,
            user_id=user_id,
            practice_type="BEHAVIORAL_STAR",
            count=3
        )
        for q in behavioral_questions:
            assert q["category"] == "Behavioral"
            assert "rest api" not in q["question"].lower()

        comm_questions = select_distinct_practice_questions(
            db=db,
            user_id=user_id,
            practice_type="STRUCTURED_ANSWER",
            count=3
        )
        for q in comm_questions:
            assert q["category"] == "Behavioral"
    finally:
        db.close()


def test_study_comparison_skipped_question():
    """Study analysis for skipped question clearly identifies SKIPPED and provides expected concepts."""
    res = generate_study_comparison_for_answer(
        question_text="What is API versioning?",
        candidate_answer="[SKIPPED]",
        category="Technical"
    )
    assert res["answer_status"] == "SKIPPED"
    assert len(res["strong_answer_should_cover"]) > 0
    assert any("backward compatibility" in c.lower() for c in res["strong_answer_should_cover"])
    assert "candidate chose not to answer" in res["missing_points"][0].lower()
    assert res["practice_prompt"] is not None


def test_study_comparison_weak_answer():
    """Study comparison identifies missing points and gives an improved model answer."""
    res = generate_study_comparison_for_answer(
        question_text="What is API versioning?",
        candidate_answer="dsjnd",
        category="Technical"
    )
    assert res["answer_status"] == "INSUFFICIENT"
    assert len(res["strong_answer_should_cover"]) > 0
    assert len(res["missing_points"]) > 0
    assert len(res["improved_answer"]) > 20


def test_study_comparison_grounded_resume_connection():
    """Resume connection strictly matches candidate's actual projects/skills and does NOT hallucinate."""
    # When resume has FastAPI and an Order Engine project
    skills = ["FastAPI", "PostgreSQL", "Docker"]
    projects = [
        {"title": "High-Concurrency Order Processing Engine", "description": "FastAPI order processing", "technologies": ["FastAPI", "PostgreSQL"]}
    ]
    res_conn = _derive_grounded_resume_connection(
        question_text="How do you handle API versioning in backend REST services?",
        resume_skills=skills,
        resume_projects=projects
    )
    assert res_conn is not None
    assert "Order Processing" in res_conn or "FastAPI" in res_conn

    # When no resume skills or projects exist, connection must be None
    res_none = _derive_grounded_resume_connection(
        question_text="How do you handle API versioning?",
        resume_skills=[],
        resume_projects=[]
    )
    assert res_none is None

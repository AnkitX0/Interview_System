import pytest
from backend.services.question_selector import select_questions
from backend.services.followup_generator import generate_followup


def test_select_questions_by_mode_and_difficulty(db_session):
    """Test filtering questions by technical mode and difficulty."""
    questions = select_questions(
        db=db_session,
        mode="technical",
        difficulty="medium",
        count=2
    )
    assert len(questions) == 2
    for q in questions:
        assert q["category"] == "Technical"


def test_select_questions_prioritizes_resume_skills(db_session):
    """Candidate with Docker skill should receive Docker question when available."""
    questions = select_questions(
        db=db_session,
        mode="technical",
        difficulty="medium",
        count=3,
        resume_skills=["Docker"]
    )
    assert len(questions) > 0
    # At least one question should reference Docker
    question_texts = [q["question"].lower() for q in questions]
    assert any("docker" in qt for qt in question_texts)


def test_followup_generator_rules():
    """Verify follow-up probing triggers based on answer gaps."""
    # 1. Very short answer -> request elaboration
    fu_short = generate_followup(
        question="Explain REST architecture.",
        answer="It is an API architectural style."
    )
    assert "elaborate" in fu_short.lower() or "detail" in fu_short.lower()

    # 2. Substantial answer without metrics (> 25 words) -> probe for metrics
    fu_no_metrics = generate_followup(
        question="Describe a challenge you faced.",
        answer="We designed a distributed microservice to process incoming orders because the previous monolithic architecture was slow and difficult to maintain. We rewrote the database queries and significantly improved overall system architecture."
    )
    assert "quantify" in fu_no_metrics.lower() or "impact" in fu_no_metrics.lower()

    # 3. Answer with metrics but no tradeoff words (> 25 words) -> probe for tradeoffs
    fu_no_tradeoffs = generate_followup(
        question="Describe a challenge you faced.",
        answer="In our production system, we deployed Redis caching to speed up requests and cache database queries, resulting in a 50% decrease in response latency across all backend services."
    )
    assert "tradeoff" in fu_no_tradeoffs.lower() or "alternative" in fu_no_tradeoffs.lower()

    # 4. Answer about team conflict with metrics & tradeoffs -> probe for communication
    fu_conflict = generate_followup(
        question="Describe a disagreement with a teammate.",
        answer="In our team, we evaluated architectural tradeoffs between PostgreSQL and MongoDB for 500k daily users. I disagreed with my team lead regarding document nesting, and we resolved the conflict through benchmarking."
    )
    assert "communication" in fu_conflict.lower() or "stakeholder" in fu_conflict.lower()

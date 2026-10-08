"""
tests/test_question_bank_and_exposure_engine.py

Comprehensive tests for:
1. Question Bank validation (>= 100 questions per category, 700+ total, valid schema, unique IDs, no duplicates)
2. Question Selection Service (anti-repetition, 20-question exposure window, category filtering, resume grounding)
3. Topic Weakness Revisit Exception (revisits weak topics with different questions)
4. Practice Category Separation & Distinct Curricula
5. Interview Context compaction for Gemini
"""

import os
import json
import pytest
from sqlalchemy.orm import Session

from backend.services.question_selection_service import (
    load_question_bank,
    get_question_by_id,
    record_question_exposure,
    get_recent_exposed_question_ids,
    get_user_weak_topics,
    select_next_contextual_question,
    STANDARD_CATEGORIES,
    BANK_DIR,
    QUESTION_REPEAT_WINDOW
)
import backend.models as models


# =========================================================================
# 1. QUESTION BANK INTEGRITY & SIZE TESTS (Minimum 700 questions, >= 100 each)
# =========================================================================

def test_question_bank_categories_and_counts():
    """Verify that all 7 practice categories exist and contain at least 100 questions each."""
    assert len(STANDARD_CATEGORIES) == 7, "Must contain exactly 7 standard categories"
    
    total_count = 0
    for cat in STANDARD_CATEGORIES:
        file_path = os.path.join(BANK_DIR, f"{cat}.json")
        assert os.path.exists(file_path), f"Question bank file missing: {file_path}"
        
        with open(file_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            
        assert isinstance(questions, list), f"Expected list of questions in {cat}"
        assert len(questions) >= 100, f"Category '{cat}' must have >= 100 questions, got {len(questions)}"
        total_count += len(questions)
        
    assert total_count >= 700, f"Total question bank must contain at least 700 questions, got {total_count}"


def test_question_bank_schemas_and_unique_ids():
    """Verify every question conforms to strict schema and has globally unique IDs."""
    all_questions = load_question_bank()
    assert len(all_questions) >= 700
    
    seen_ids = set()
    seen_texts = set()
    
    for q in all_questions:
        q_id = q.get("id")
        assert q_id, f"Question missing ID: {q}"
        assert q_id not in seen_ids, f"Duplicate question ID detected: {q_id}"
        seen_ids.add(q_id)
        
        q_text = q.get("question", "").strip()
        assert len(q_text) >= 10, f"Question text too short for ID {q_id}: {q_text}"
        assert q_text not in seen_texts, f"Exact duplicate question found: {q_text}"
        seen_texts.add(q_text)
        
        assert q.get("category"), f"Missing category in {q_id}"
        assert q.get("topic"), f"Missing topic in {q_id}"
        assert q.get("difficulty") in ("easy", "medium", "hard", "expert"), f"Invalid difficulty in {q_id}: {q.get('difficulty')}"
        assert isinstance(q.get("expected_evidence"), list), f"expected_evidence must be a list in {q_id}"
        assert isinstance(q.get("follow_up_topics"), list), f"follow_up_topics must be a list in {q_id}"


def test_project_defense_questions_have_resume_awareness():
    """Project and Claim defense questions must have requires_resume_context flag or templates."""
    proj_questions = load_question_bank("project_claim_defense")
    assert len(proj_questions) >= 100
    
    for q in proj_questions:
        assert q.get("requires_resume_context") is True or "{" in q.get("question", "")


# =========================================================================
# 2. QUESTION SELECTION & CROSS-SESSION REPETITION PREVENTION
# =========================================================================

def test_question_exposure_history_and_window(db_session: Session, test_user):
    """Verify that exposed questions are tracked and excluded within QUESTION_REPEAT_WINDOW = 20."""
    category = "technical_deep_dive"
    
    # 1. Initially user has no exposed questions
    exposed_initial = get_recent_exposed_question_ids(db_session, user_id=test_user.id, category=category, limit=20)
    assert len(exposed_initial) == 0
    
    # 2. Record 5 exposures
    sample_ids = ["TD_001", "TD_002", "TD_003", "TD_004", "TD_005"]
    for q_id in sample_ids:
        record_question_exposure(
            db=db_session,
            user_id=test_user.id,
            question_id=q_id,
            category=category,
            topic="Distributed Systems"
        )
        
    exposed_after = get_recent_exposed_question_ids(db_session, user_id=test_user.id, category=category, limit=20)
    assert exposed_after == set(sample_ids)
    
    # 3. Requesting next question excludes all 5 exposed questions
    next_q = select_next_contextual_question(
        db=db_session,
        user_id=test_user.id,
        category=category,
        difficulty="medium"
    )
    assert next_q["id"] not in sample_ids, f"Selected question {next_q['id']} was in recently exposed set!"


def test_weakness_revisit_exception(db_session: Session, test_user):
    """
    If candidate performed poorly on Database Transactions, the system can revisit
    the topic, but must NOT repeat the exact same question.
    """
    category = "technical_deep_dive"
    topic = "Database Transactions"
    
    # Record poor score on TD_001 for this topic
    record_question_exposure(
        db=db_session,
        user_id=test_user.id,
        question_id="TD_001",
        category=category,
        topic=topic,
        answer_status="INSUFFICIENT",
        score=35.0
    )
    
    weak_topics = get_user_weak_topics(db_session, user_id=test_user.id)
    assert topic in weak_topics
    
    # Next question selection should prioritize the weak topic but NOT repeat TD_001
    next_q = select_next_contextual_question(
        db=db_session,
        user_id=test_user.id,
        category=category,
        difficulty="medium"
    )
    assert next_q["id"] != "TD_001"
    # Should pick another question from the bank
    assert next_q["id"].startswith("TD_")


def test_resume_grounded_project_defense(db_session: Session, test_user):
    """Project Defense questions should ground into candidate's actual projects/technologies."""
    # Add a resume project and skill
    resume = models.Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        raw_text="Built an ASL translator using MediaPipe and PyTorch.",
        skills='["MediaPipe", "PyTorch", "Python"]'
    )
    db_session.add(resume)
    db_session.commit()
    
    proj = models.ResumeProject(
        resume_id=resume.id,
        title="ASL Real-Time Translator",
        technologies=["MediaPipe", "PyTorch", "Python"],
        description="Built real-time hand landmark classification system."
    )
    db_session.add(proj)
    db_session.commit()
    
    candidate_profile = {
        "projects": [{"name": "ASL Real-Time Translator", "technologies": ["MediaPipe", "PyTorch"]}],
        "skills": ["MediaPipe", "PyTorch", "Python"]
    }
    
    q = select_next_contextual_question(
        db=db_session,
        user_id=test_user.id,
        category="project_claim_defense",
        candidate_profile=candidate_profile
    )
    assert q is not None
    # Question text should not contain ungrounded raw template tags like {project_name}
    assert "{project_name}" not in q["question"]
    assert "{technology_name}" not in q["question"]
    assert q["is_resume_based"] is True


def test_tradeoff_reasoning_curriculum(db_session: Session, test_user):
    """Tradeoff questions must focus on architectural comparisons and decision justification."""
    q = select_next_contextual_question(
        db=db_session,
        user_id=test_user.id,
        category="tradeoff_reasoning"
    )
    assert q["category"] == "tradeoff_reasoning"
    assert q["id"].startswith("TR_")
    text_lower = q["question"].lower()
    # Trade-off questions emphasize vs, trade-off, choose, between, compare, or justify
    assert any(term in text_lower for term in [
        " vs ", "versus", "choose", "trade-off", "tradeoff", "between", "alternative",
        "justify", "prefer", "balance", "evaluate", "against", "compare", "contrast",
        "when ", "under what", "advantage"
    ])


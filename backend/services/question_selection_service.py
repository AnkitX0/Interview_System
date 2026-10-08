"""
backend/services/question_selection_service.py

Persistent Question Bank & Contextual Selection Engine.
Manages 700+ curated questions across 7 categories:
1. technical_deep_dive
2. tradeoff_reasoning
3. followup_probe_defense
4. project_claim_defense
5. structured_communication
6. behavioral_scenarios
7. high_urgency_pressure

Features:
- Configurable history window (QUESTION_REPEAT_WINDOW = 20)
- Topic weakness revisit with distinct questions
- Resume-aware filtering (70% profile-relevant, 30% broad role)
- Compact InterviewContext for Gemini contextualization
- Deterministic fallback when Gemini is offline
"""

import os
import json
import logging
import random
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

import backend.models as models
from backend.services.llm_gemini_service import call_gemini_json

logger = logging.getLogger("interview_system.question_selection")

BANK_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "question_bank")
QUESTION_REPEAT_WINDOW = 20

# Cache for question bank in memory
_QUESTION_BANK_CACHE: Dict[str, List[Dict[str, Any]]] = {}

CATEGORY_FILE_MAP = {
    "technical_deep_dive": "technical_deep_dive",
    "technical": "technical_deep_dive",
    "tradeoff_reasoning": "tradeoff_reasoning",
    "tradeoff": "tradeoff_reasoning",
    "followup_probe_defense": "followup_probe_defense",
    "followup": "followup_probe_defense",
    "project_claim_defense": "project_claim_defense",
    "project": "project_claim_defense",
    "structured_communication": "structured_communication",
    "communication": "structured_communication",
    "behavioral_scenarios": "behavioral_scenarios",
    "behavioral": "behavioral_scenarios",
    "high_urgency_pressure": "high_urgency_pressure",
    "pressure": "high_urgency_pressure"
}

STANDARD_CATEGORIES = [
    "technical_deep_dive",
    "tradeoff_reasoning",
    "followup_probe_defense",
    "project_claim_defense",
    "structured_communication",
    "behavioral_scenarios",
    "high_urgency_pressure"
]


def load_question_bank(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Loads questions for a category or the entire bank. Caches in memory.
    """
    global _QUESTION_BANK_CACHE
    if not _QUESTION_BANK_CACHE:
        for cat_name in STANDARD_CATEGORIES:
            filename = f"{cat_name}.json"
            filepath = os.path.join(BANK_DIR, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        _QUESTION_BANK_CACHE[cat_name] = data
                except Exception as e:
                    logger.error("Failed to load question bank file %s: %s", filepath, e)
                    _QUESTION_BANK_CACHE[cat_name] = []
            else:
                logger.warning("Question bank file not found: %s", filepath)
                _QUESTION_BANK_CACHE[cat_name] = []

    if category:
        norm_cat = CATEGORY_FILE_MAP.get(category.lower().strip(), category.lower().strip())
        return _QUESTION_BANK_CACHE.get(norm_cat, [])

    # Return all combined
    all_q = []
    for q_list in _QUESTION_BANK_CACHE.values():
        all_q.extend(q_list)
    return all_q


def get_question_by_id(question_id: str) -> Optional[Dict[str, Any]]:
    """Finds a specific question by ID across all categories."""
    all_questions = load_question_bank()
    for q in all_questions:
        if q.get("id") == question_id:
            return q
    return None


def record_question_exposure(
    db: Session,
    user_id: int,
    question_id: str,
    category: str,
    session_id: Optional[int] = None,
    topic: Optional[str] = None,
    answer_status: Optional[str] = None,
    score: Optional[float] = None
) -> models.QuestionExposureHistory:
    """
    Records that a question was presented to a candidate to prevent near-term repetition.
    """
    norm_cat = CATEGORY_FILE_MAP.get(category.lower().strip(), category.lower().strip())
    exposure = models.QuestionExposureHistory(
        user_id=user_id,
        question_id=question_id,
        category=norm_cat,
        session_id=session_id,
        topic=topic,
        answer_status=answer_status,
        score=score
    )
    db.add(exposure)
    try:
        db.commit()
        db.refresh(exposure)
    except Exception as e:
        db.rollback()
        logger.warning("Failed to record question exposure: %s", e)
    return exposure


def update_exposure_evaluation(
    db: Session,
    user_id: int,
    question_id: str,
    session_id: Optional[int],
    answer_status: str,
    score: float
) -> None:
    """Updates evaluation outcomes for an exposed question turn."""
    exp = (
        db.query(models.QuestionExposureHistory)
        .filter(
            models.QuestionExposureHistory.user_id == user_id,
            models.QuestionExposureHistory.question_id == question_id,
            models.QuestionExposureHistory.session_id == session_id
        )
        .order_by(models.QuestionExposureHistory.timestamp.desc())
        .first()
    )
    if exp:
        exp.answer_status = answer_status
        exp.score = score
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("Failed to update exposure score: %s", e)


def get_recent_exposed_question_ids(
    db: Session,
    user_id: int,
    category: Optional[str] = None,
    limit: int = QUESTION_REPEAT_WINDOW
) -> Set[str]:
    """
    Returns set of question IDs recently exposed to the candidate.
    """
    try:
        query = (
            db.query(models.QuestionExposureHistory.question_id)
            .filter(models.QuestionExposureHistory.user_id == user_id)
        )
        if category:
            norm_cat = CATEGORY_FILE_MAP.get(category.lower().strip(), category.lower().strip())
            query = query.filter(models.QuestionExposureHistory.category == norm_cat)

        rows = query.order_by(models.QuestionExposureHistory.timestamp.desc()).limit(limit).all()
        return {r[0] for r in rows if r[0]}
    except Exception as e:
        logger.debug("Could not read recent exposed questions: %s", e)
        return set()


def get_user_weak_topics(db: Session, user_id: int) -> List[str]:
    """Identifies topics where the candidate previously scored < 60.0."""
    try:
        rows = (
            db.query(models.QuestionExposureHistory.topic)
            .filter(
                models.QuestionExposureHistory.user_id == user_id,
                models.QuestionExposureHistory.score.isnot(None),
                models.QuestionExposureHistory.score < 60.0
            )
            .order_by(models.QuestionExposureHistory.timestamp.desc())
            .limit(10)
            .all()
        )
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        logger.debug("Could not read user weak topics: %s", e)
        return []


def _ground_project_question(
    template_question: str,
    resume_skills: List[str],
    resume_projects: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """
    Substitutes {project_name} and {technology_name} using genuine resume context.
    Strictly avoids fabricating unlisted tools or projects.
    """
    proj_name = "your primary backend service"
    tech_name = "your core stack"

    if resume_projects:
        first_proj = resume_projects[0]
        p_title = first_proj.get("title") or first_proj.get("name")
        if p_title:
            proj_name = p_title
        p_techs = first_proj.get("technologies") or []
        if p_techs:
            tech_name = p_techs[0]
        elif resume_skills:
            tech_name = resume_skills[0]
    elif resume_skills:
        tech_name = resume_skills[0]

    q_text = template_question.replace("{project_name}", f"'{proj_name}'")
    q_text = q_text.replace("{technology_name}", tech_name)
    return q_text, proj_name


class QuestionSelectionService:
    """
    Production-grade Question Selection Engine prioritizing:
    1. Unresolved previous turn points (follow-ups)
    2. Resume claims requiring verification
    3. Weakness topics (asking a distinct question on the same topic)
    4. Resume-profile alignment (70% candidate stack, 30% broad role)
    5. Non-repeated questions within the configurable window
    6. Contextual framing by Gemini
    """

    @classmethod
    def select_next_question(
        cls,
        db: Session,
        user_id: int,
        category: str = "technical_deep_dive",
        session_id: Optional[int] = None,
        target_role: str = "Software Engineer",
        difficulty: str = "medium",
        resume_skills: Optional[List[str]] = None,
        resume_projects: Optional[List[Dict[str, Any]]] = None,
        recent_turns: Optional[List[Dict[str, Any]]] = None,
        unresolved_points: Optional[List[str]] = None,
        allow_gemini_adaptation: bool = True
    ) -> Dict[str, Any]:
        norm_cat = CATEGORY_FILE_MAP.get(category.lower().strip(), "technical_deep_dive")
        questions = load_question_bank(norm_cat)

        if not questions:
            # Fallback if file missing
            questions = load_question_bank("technical_deep_dive")

        # 1. Fetch recent exposures to prevent repeats
        recently_used_ids = get_recent_exposed_question_ids(db, user_id, category=norm_cat, limit=QUESTION_REPEAT_WINDOW)
        
        # In-session question history
        in_session_ids = set()
        if session_id:
            session_questions = (
                db.query(models.InterviewQuestion.id, models.InterviewQuestion.question_text)
                .filter(models.InterviewQuestion.session_id == session_id)
                .all()
            )
            for sq in session_questions:
                in_session_ids.add(str(sq[0]))

        # 2. Check for Weakness Revisit Exception
        weak_topics = get_user_weak_topics(db, user_id)
        candidate_pool = [q for q in questions if q.get("id") not in recently_used_ids and q.get("id") not in in_session_ids]

        selected_q = None
        selection_reason = "standard_bank_selection"

        # Check if we should revisit a weak topic with a DIFFERENT question
        if weak_topics and random.random() < 0.35:
            for w_topic in weak_topics:
                matching_weak = [
                    q for q in candidate_pool
                    if q.get("topic", "").lower() == w_topic.lower()
                ]
                if matching_weak:
                    selected_q = random.choice(matching_weak)
                    selection_reason = f"weakness_revisit_topic_{w_topic}"
                    break

        # 3. Resume-aware matching (70% profile relevant, 30% general role)
        if not selected_q and candidate_pool:
            is_resume_focused = random.random() < 0.70
            profile_tokens = set()
            if resume_skills:
                for s in resume_skills:
                    profile_tokens.add(s.lower())
            if resume_projects:
                for p in resume_projects:
                    for t in (p.get("technologies") or []):
                        profile_tokens.add(t.lower())

            if is_resume_focused and profile_tokens:
                relevance_scored = []
                for q in candidate_pool:
                    q_skills = [s.lower() for s in q.get("skills", [])]
                    match_count = sum(1 for s in q_skills if s in profile_tokens or any(pt in s for pt in profile_tokens))
                    if match_count > 0:
                        relevance_scored.append((match_count, q))

                if relevance_scored:
                    relevance_scored.sort(key=lambda x: x[0], reverse=True)
                    # Pick from top matching tier
                    top_matches = [q for score, q in relevance_scored if score == relevance_scored[0][0]]
                    selected_q = random.choice(top_matches)
                    selection_reason = "resume_profile_match"

        # 4. Filter by difficulty if pool allows
        if not selected_q and candidate_pool:
            diff_pool = [q for q in candidate_pool if q.get("difficulty") == difficulty]
            if diff_pool:
                selected_q = random.choice(diff_pool)
            else:
                selected_q = random.choice(candidate_pool)
            selection_reason = "category_difficulty_pool"

        # If all questions in pool were recently exposed, relax window to un-exhausted pool
        if not selected_q:
            unexhausted = [q for q in questions if q.get("id") not in in_session_ids]
            selected_q = random.choice(unexhausted) if unexhausted else random.choice(questions)
            selection_reason = "window_relaxed_pool"

        # 5. Ground Project Claim Defense questions
        raw_question_text = selected_q.get("question", "")
        grounded_meta = ""
        if norm_cat == "project_claim_defense" or selected_q.get("requires_resume_context"):
            raw_question_text, proj_ref = _ground_project_question(
                raw_question_text,
                resume_skills=resume_skills or [],
                resume_projects=resume_projects or []
            )
            grounded_meta = f"Project Defense · {proj_ref}"
        elif norm_cat == "followup_probe_defense":
            grounded_meta = "Follow-up Probe"
        elif norm_cat == "tradeoff_reasoning":
            grounded_meta = "Trade-off Reasoning"
        elif norm_cat == "behavioral_scenarios":
            grounded_meta = "Behavioral Scenario"
        elif norm_cat == "high_urgency_pressure":
            grounded_meta = "High-Urgency Pressure"
        else:
            grounded_meta = "Technical Deep Dive"

        # 6. Gemini Contextual Adaptation ("How should I ask this for THIS candidate?")
        final_question_text = raw_question_text
        if allow_gemini_adaptation and recent_turns:
            adapted = cls._adapt_question_with_gemini(
                base_question=raw_question_text,
                category=norm_cat,
                target_role=target_role,
                resume_skills=resume_skills,
                resume_projects=resume_projects,
                recent_turns=recent_turns,
                unresolved_points=unresolved_points
            )
            if adapted:
                final_question_text = adapted
                selection_reason += "_gemini_contextualized"

        # Record exposure in DB
        record_question_exposure(
            db=db,
            user_id=user_id,
            question_id=selected_q.get("id", "CUSTOM"),
            category=norm_cat,
            session_id=session_id,
            topic=selected_q.get("topic", "General")
        )

        return {
            "id": selected_q.get("id", "TD_001"),
            "category": norm_cat,
            "topic": selected_q.get("topic", "System Architecture"),
            "difficulty": selected_q.get("difficulty", difficulty),
            "question": final_question_text,
            "raw_question": raw_question_text,
            "question_type": selected_q.get("question_type", "conceptual"),
            "skills": selected_q.get("skills", []),
            "expected_evidence": selected_q.get("expected_evidence", []),
            "follow_up_topics": selected_q.get("follow_up_topics", []),
            "caption": grounded_meta,
            "is_resume_based": True if (norm_cat in ("project_claim_defense", "project") or selected_q.get("requires_resume_context") or "Resume" in (grounded_meta or "") or "Project" in (grounded_meta or "")) else False,
            "selection_reason": selection_reason
        }

    @classmethod
    def _adapt_question_with_gemini(
        cls,
        base_question: str,
        category: str,
        target_role: str,
        resume_skills: Optional[List[str]],
        resume_projects: Optional[List[Dict[str, Any]]],
        recent_turns: List[Dict[str, Any]],
        unresolved_points: Optional[List[str]]
    ) -> Optional[str]:
        """
        Builds a compact InterviewContext and uses Gemini to naturally contextualize
        the interviewer's phrasing. Falls back to base question if offline.
        """
        # Compact turn summary (last 2 turns max to keep token footprint tiny)
        compact_turns = []
        for t in recent_turns[-2:]:
            q_snippet = (t.get("question_text") or t.get("question") or "")[:70]
            a_snippet = (t.get("transcript") or t.get("answer") or "")[:80]
            compact_turns.append(f"Q: {q_snippet} -> A: {a_snippet}")

        context_prompt = (
            f"You are a professional technical interviewer for a {target_role} position.\n"
            f"Selected Question from Bank: \"{base_question}\"\n"
            f"Candidate Skills: {', '.join((resume_skills or [])[:5])}\n"
            f"Recent Conversation:\n" + "\n".join(compact_turns) + "\n"
        )
        if unresolved_points:
            context_prompt += f"Unresolved gaps: {', '.join(unresolved_points[:2])}\n"

        context_prompt += (
            "\nAdapt the question so it transitions naturally from the candidate's previous response, "
            "maintaining the exact core technical concept of the question.\n"
            "Keep the phrasing concise (1-2 sentences). Do not mention that this was from a question bank.\n"
            "Return valid JSON:\n"
            "{\"adapted_question\": \"...\"}"
        )

        try:
            res = call_gemini_json(context_prompt, timeout=2.5)
            if res and isinstance(res, dict) and res.get("adapted_question"):
                return res["adapted_question"].strip()
        except Exception as e:
            logger.debug("Gemini adaptation skipped: %s", e)
        return None


def select_next_contextual_question(
    db: Session,
    user_id: int,
    category: str = "technical_deep_dive",
    session_id: Optional[int] = None,
    target_role: str = "Software Engineer",
    difficulty: str = "medium",
    candidate_profile: Optional[Dict[str, Any]] = None,
    resume_skills: Optional[List[str]] = None,
    resume_projects: Optional[List[Dict[str, Any]]] = None,
    recent_turns: Optional[List[Dict[str, Any]]] = None,
    unresolved_points: Optional[List[str]] = None,
    allow_gemini_adaptation: bool = False
) -> Dict[str, Any]:
    skills = resume_skills or (candidate_profile.get("skills") if candidate_profile else None)
    projects = resume_projects or (candidate_profile.get("projects") if candidate_profile else None)
    return QuestionSelectionService.select_next_question(
        db=db,
        user_id=user_id,
        category=category,
        session_id=session_id,
        target_role=target_role,
        difficulty=difficulty,
        resume_skills=skills,
        resume_projects=projects,
        recent_turns=recent_turns,
        unresolved_points=unresolved_points,
        allow_gemini_adaptation=allow_gemini_adaptation
    )


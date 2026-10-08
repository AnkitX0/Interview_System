"""
backend/services/question_selector.py

Resume-Aware Question Selector backed by the persistent 700+ Question Bank.
Integrates with QuestionSelectionService to prevent cross-session repetition.
"""

import random
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import backend.models as models
from backend.services.question_selection_service import (
    load_question_bank,
    get_recent_exposed_question_ids,
    record_question_exposure,
    CATEGORY_FILE_MAP
)


def select_questions(
    db: Session,
    mode: str = "practice",
    difficulty: str = "medium",
    count: int = 3,
    resume_skills: Optional[List[str]] = None,
    target_role: Optional[str] = None,
    user_id: Optional[int] = None,
    resume_projects: Optional[List[Dict[str, Any]]] = None,
    resume_claims: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Selects resume-aware dynamic interview questions from the 700+ Question Bank and candidate profile.
    Prioritizes project defense and claim verification for candidates with uploaded resumes.
    Guarantees no repetition within the session and respects candidate profile.
    """
    mode_low = (mode or "technical").lower().strip()
    category_map = {
        "technical": "technical_deep_dive",
        "tradeoff": "tradeoff_reasoning",
        "behavioral": "behavioral_scenarios",
        "pressure": "high_urgency_pressure",
        "communication": "structured_communication",
        "hr": "behavioral_scenarios",
        "practice": "technical_deep_dive"
    }
    cat_key = category_map.get(mode_low, "technical_deep_dive")
    bank_questions = load_question_bank(cat_key)
    if not bank_questions:
        bank_questions = load_question_bank("technical_deep_dive")

    category_title = "Technical" if mode_low in ("technical", "tradeoff", "practice") else (
        "HR" if mode_low == "hr" else ("Pressure" if mode_low == "pressure" else "Behavioral")
    )

    selected = []
    seen_texts = set()
    profile_skills = [s.lower() for s in (resume_skills or [])]

    # 0. Contextual Resume Defense: Prioritize candidate's actual projects and claims
    if mode_low in ("technical", "tradeoff", "practice"):
        if resume_projects:
            for proj in resume_projects:
                if len(selected) >= max(1, count // 2):
                    break
                p_title = (proj.get("title") or "").strip()
                p_techs = proj.get("technologies") or []
                if not p_title:
                    continue
                tech_str = ", ".join(p_techs[:3]) if p_techs else "its architectural pipeline"
                q_text = (
                    f"In your project '{p_title}' utilizing {tech_str}: walk me through the system architecture, "
                    f"how the core data pipeline was implemented, and what key technical trade-offs you evaluated."
                )
                if q_text not in seen_texts:
                    seen_texts.add(q_text)
                    selected.append({
                        "id": len(selected) + 1,
                        "bank_id": f"RESUME_PROJ_{len(selected) + 1}",
                        "question": q_text,
                        "question_text": q_text,
                        "category": category_title,
                        "topic": f"{p_title} Architecture",
                        "difficulty": difficulty,
                        "question_type": "resume_defense",
                        "skills": p_techs if p_techs else profile_skills[:3],
                        "expected_evidence": ["Component communication", "Trade-off justification", "Implementation ownership"],
                        "follow_up_topics": ["Bottlenecks", "Failure recovery", "Production scaling"],
                        "time_limit_seconds": 45 if mode_low == "pressure" else 90,
                        "caption": "Resume Project Defense"
                    })
        elif resume_claims:
            for claim in resume_claims:
                if len(selected) >= max(1, count // 2):
                    break
                c_text = (claim.get("claim_text") or "").strip()
                if not c_text:
                    continue
                if c_text.endswith("."):
                    c_text = c_text[:-1]
                q_text = (
                    f"Regarding your resume claim: '{c_text}' — walk me through the underlying system architecture, "
                    f"the specific methodology or metrics you evaluated, and how you ensured correctness under edge conditions."
                )
                if q_text not in seen_texts:
                    seen_texts.add(q_text)
                    selected.append({
                        "id": len(selected) + 1,
                        "bank_id": f"RESUME_CLAIM_{len(selected) + 1}",
                        "question": q_text,
                        "question_text": q_text,
                        "category": category_title,
                        "topic": "Claim Verification",
                        "difficulty": difficulty,
                        "question_type": "resume_defense",
                        "skills": claim.get("technologies", []) or profile_skills[:3],
                        "expected_evidence": ["Metric verification", "System design details", "Edge cases"],
                        "follow_up_topics": ["Error rates", "Benchmarks", "Scaling"],
                        "time_limit_seconds": 45 if mode_low == "pressure" else 90,
                        "caption": "Resume Claim Defense"
                    })

    # 1. First check if database has seeded QuestionBank items (e.g. test fixtures or custom DB questions)
    db_items = []
    try:
        q_query = db.query(models.QuestionBank)
        if mode_low == "technical":
            q_query = q_query.filter(models.QuestionBank.category == "Technical")
        elif mode_low == "hr":
            q_query = q_query.filter(models.QuestionBank.category == "HR")
        elif mode_low == "pressure":
            q_query = q_query.filter(models.QuestionBank.category.in_(["Pressure", "Behavioral"]))
        elif mode_low == "behavioral":
            q_query = q_query.filter(models.QuestionBank.category == "Behavioral")
        
        all_db = q_query.all()
        if all_db:
            # Score DB questions by resume skill match and difficulty
            scored_db = []
            for db_q in all_db:
                q_text = db_q.question_text.lower()
                overlap = sum(1 for s in profile_skills if s in q_text)
                diff_match = 1 if (db_q.difficulty or "").lower() == (difficulty or "medium").lower() else 0
                scored_db.append((overlap * 2 + diff_match, db_q))
            scored_db.sort(key=lambda x: (x[0], random.random()), reverse=True)
            db_items = [item[1] for item in scored_db]
    except Exception:
        db_items = []

    # If any DB questions strongly match resume skills or difficulty, include them
    if db_items and (profile_skills or len(bank_questions) == 0):
        for db_q in db_items:
            q_text = db_q.question_text.strip()
            if q_text not in seen_texts:
                # If skills requested, require skill match for first pick if possible
                if profile_skills and not any(s in q_text.lower() for s in profile_skills) and len(selected) == 0:
                    # check if any later db_q matches
                    matching_later = [q for q in db_items if any(s in q.question_text.lower() for s in profile_skills)]
                    if matching_later:
                        db_q = matching_later[0]
                        q_text = db_q.question_text.strip()
                seen_texts.add(q_text)
                selected.append({
                    "id": db_q.id,
                    "bank_id": f"DB_{db_q.id}",
                    "question": q_text,
                    "question_text": q_text,
                    "category": category_title,
                    "topic": getattr(db_q, "role", None) or "Core Technical",
                    "difficulty": db_q.difficulty or difficulty,
                    "question_type": "conceptual",
                    "skills": [s for s in profile_skills if s in q_text.lower()],
                    "expected_evidence": [],
                    "follow_up_topics": [],
                    "time_limit_seconds": 45 if mode_low == "pressure" else 90,
                    "caption": "Technical Deep Dive" if mode_low == "technical" else f"{category_title} Question"
                })
                if len(selected) >= count:
                    break

    # 2. If needed, draw from the 700+ Question Bank
    if len(selected) < count:
        recently_exposed = set()
        if user_id:
            try:
                recently_exposed = get_recent_exposed_question_ids(db, user_id=user_id, category=cat_key, limit=20)
            except Exception:
                recently_exposed = set()

        available = [q for q in bank_questions if q.get("id") not in recently_exposed]
        if len(available) < (count - len(selected)):
            available = list(bank_questions)

        scored = []
        for q in available:
            q_skills = [s.lower() for s in q.get("skills", [])]
            q_text_low = q.get("question", "").lower()
            overlap = sum(1 for s in profile_skills if any(ps in s or s in ps for ps in q_skills) or s in q_text_low)
            diff_match = 1 if q.get("difficulty", "").lower() == (difficulty or "medium").lower() else 0
            scored.append((overlap * 2 + diff_match, q))

        scored.sort(key=lambda x: (x[0], random.random()), reverse=True)

        for _, q in scored:
            q_text = q.get("question", "").strip()
            if q_text not in seen_texts:
                seen_texts.add(q_text)
                item = {
                    "id": len(selected) + 1,
                    "bank_id": q.get("id"),
                    "question": q_text,
                    "question_text": q_text,
                    "category": category_title,
                    "topic": q.get("topic", "System Design"),
                    "difficulty": q.get("difficulty", difficulty),
                    "question_type": q.get("question_type", "conceptual"),
                    "skills": q.get("skills", []),
                    "expected_evidence": q.get("expected_evidence", []),
                    "follow_up_topics": q.get("follow_up_topics", []),
                    "time_limit_seconds": 45 if mode_low == "pressure" else 90,
                    "caption": "Technical Deep Dive" if mode_low == "technical" else f"{category_title} Question"
                }
                selected.append(item)
                if user_id:
                    try:
                        record_question_exposure(
                            db=db,
                            user_id=user_id,
                            question_id=q.get("id", "BANK"),
                            category=cat_key,
                            topic=q.get("topic")
                        )
                    except Exception:
                        pass
                if len(selected) >= count:
                    break

    # If still empty, use fallback
    if not selected and db_items:
        for db_q in db_items[:count]:
            selected.append({
                "id": db_q.id,
                "question": db_q.question_text,
                "question_text": db_q.question_text,
                "category": category_title,
                "difficulty": db_q.difficulty
            })

    return selected[:count]
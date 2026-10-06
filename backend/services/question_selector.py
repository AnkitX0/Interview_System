import random
from typing import List, Optional
from sqlalchemy.orm import Session
import backend.models as models

FALLBACK_QUESTIONS = [
    {"question": "Tell me about yourself and your background in software engineering.", "category": "HR", "difficulty": "easy"},
    {"question": "Explain REST API architecture and how HTTP methods are utilized.", "category": "Technical", "difficulty": "medium"},
    {"question": "Describe a challenging technical problem you encountered and how you resolved it.", "category": "Behavioral", "difficulty": "medium"},
    {"question": "What is the difference between SQL and NoSQL databases, and when would you choose each?", "category": "Technical", "difficulty": "medium"},
    {"question": "How do you handle strict deadlines when faced with scope creep or unexpected blockers?", "category": "Behavioral", "difficulty": "hard"}
]


def select_questions(
    db: Session,
    mode: str = "practice",
    difficulty: str = "medium",
    count: int = 3,
    resume_skills: Optional[List[str]] = None,
    target_role: Optional[str] = None
) -> List[dict]:
    """
    Selects resume-aware dynamic interview questions from QuestionBank with fallback.
    """
    query = db.query(models.QuestionBank)

    if mode.lower() == "technical":
        query = query.filter(models.QuestionBank.category == "Technical")
    elif mode.lower() == "hr":
        query = query.filter(models.QuestionBank.category == "HR")
    elif mode.lower() == "pressure":
        query = query.filter(models.QuestionBank.category.in_(["Pressure", "Behavioral"]))
    elif mode.lower() == "behavioral":
        query = query.filter(models.QuestionBank.category == "Behavioral")

    if difficulty:
        query = query.filter(models.QuestionBank.difficulty == difficulty.lower())

    all_matches = query.all()

    # If difficulty filter was too strict and returned few questions, relax difficulty
    if len(all_matches) < count:
        fallback_query = db.query(models.QuestionBank)
        if mode.lower() == "technical":
            fallback_query = fallback_query.filter(models.QuestionBank.category == "Technical")
        elif mode.lower() == "hr":
            fallback_query = fallback_query.filter(models.QuestionBank.category == "HR")
        all_matches = fallback_query.all()

    # Prioritize resume skills if available
    selected = []
    if resume_skills and len(resume_skills) > 0 and all_matches:
        skill_matched = []
        for q in all_matches:
            if any(s.lower() in q.question_text.lower() for s in resume_skills):
                skill_matched.append(q)
        if skill_matched:
            sample_size = min(len(skill_matched), max(1, count // 2))
            selected.extend(random.sample(skill_matched, sample_size))

    # Fill remaining quota
    remaining_pool = [q for q in all_matches if q not in selected]
    needed = count - len(selected)
    if remaining_pool and needed > 0:
        if len(remaining_pool) <= needed:
            selected.extend(remaining_pool)
        else:
            selected.extend(random.sample(remaining_pool, needed))

    if not selected:
        # Fallback to predefined questions
        return [{"id": i + 1, "question": q["question"], "category": q["category"], "difficulty": q["difficulty"]} for i, q in enumerate(FALLBACK_QUESTIONS[:count])]

    return [
        {
            "id": q.id,
            "question": q.question_text,
            "category": q.category,
            "difficulty": q.difficulty
        }
        for q in selected[:count]
    ]
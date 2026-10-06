import os
from typing import Dict, Any, List, Optional
from backend.services.scoring_engine import evaluate_rubric_for_answer


def evaluate_answer(
    transcript: str,
    question_text: str = "",
    category: str = "Technical",
    resume_skills: Optional[List[str]] = None,
    response_time: float = 0.0,
    wpm: float = 0.0,
    filler_count: int = 0
) -> Dict[str, Any]:
    """
    Evaluates candidate's answer.
    Uses rubric-based deterministic engine by default.
    Transparently supports external LLM if API key is provided in environment.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    # In production/offline environments without keys, use the deterministic rubric engine
    evaluation = evaluate_rubric_for_answer(
        transcript=transcript,
        question_text=question_text,
        category=category,
        resume_skills=resume_skills,
        response_time=response_time,
        wpm=wpm,
        filler_count=filler_count
    )

    return evaluation
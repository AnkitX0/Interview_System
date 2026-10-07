import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("interview_system.llm_provider")


class LLMQuestionOutput(BaseModel):
    question: str
    question_type: str = "technical_followup"
    topic: str = "general"
    difficulty: str = "medium"
    reason: str = "Adaptive follow-up based on candidate's previous response"
    expected_focus: List[str] = Field(default_factory=list)


def generate_llm_adaptive_question(
    target_role: str,
    difficulty: str,
    previous_question: str,
    previous_answer: str,
    observed_weakness: Optional[str] = None,
    candidate_skills: Optional[List[str]] = None,
    unresolved_points: Optional[List[str]] = None,
    resume_claims: Optional[List[str]] = None,
    timeout: int = 6
) -> Optional[LLMQuestionOutput]:
    """
    Uses Gemini LLM (via GEMINI_API_KEY) to generate a structured adaptive follow-up
    or next interview question grounded in interview memory. Validates JSON output with Pydantic.
    Returns None if GEMINI_API_KEY is absent or if LLM call/validation fails,
    triggering the deterministic question engine.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None

    unresolved_str = "; ".join(unresolved_points) if unresolved_points else "None"
    claims_str = "; ".join(resume_claims[:3]) if resume_claims else "None"

    prompt = (
        f"You are a realistic, senior technical interviewer for the role of {target_role}.\n"
        f"Difficulty: {difficulty}\n"
        f"Candidate Resume Claims: {claims_str}\n"
        f"Previous Question Asked: {previous_question}\n"
        f"Candidate's Response: {previous_answer}\n"
        f"Unresolved Points / Evasions: {unresolved_str}\n"
        f"Observed Weakness: {observed_weakness or 'None'}\n"
        f"Candidate Core Skills: {', '.join(candidate_skills or [])}\n\n"
        f"System Instructions:\n"
        f"1. Ask exactly ONE professional interview question.\n"
        f"2. If candidate evaded or left unresolved points, directly return to the unresolved issue.\n"
        f"3. If candidate gave a strong technical response, increase depth (trade-offs, production SLAs, failure handling, 10x scale).\n"
        f"4. Do not repeat previous questions.\n"
        f"5. Return ONLY valid JSON in the following exact format without markdown code blocks:\n"
        f'{{\n'
        f'  "question": "question text",\n'
        f'  "question_type": "technical_followup",\n'
        f'  "topic": "topic name",\n'
        f'  "difficulty": "{difficulty}",\n'
        f'  "reason": "explanation of why this question follows",\n'
        f'  "expected_focus": ["key concept 1", "key concept 2"]\n'
        f'}}\n'
    )

    from backend.config import GEMINI_MODEL
    models_to_try = [
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    ]

    for model_url in models_to_try:
        try:
            import urllib.request
            url = f"{model_url}?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300, "responseMimeType": "application/json"}
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)

                parsed_json = json.loads(raw_text)
                return LLMQuestionOutput(**parsed_json)
        except Exception as exc:
            logger.warning("LLM model endpoint notice (%s): %s", model_url, exc)
            continue

    return None

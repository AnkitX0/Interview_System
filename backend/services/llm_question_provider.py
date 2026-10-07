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
    timeout: int = 6
) -> Optional[LLMQuestionOutput]:
    """
    Uses Gemini LLM (via GEMINI_API_KEY) to generate a structured adaptive follow-up
    or next interview question. Validates JSON output with Pydantic.
    Returns None if GEMINI_API_KEY is absent or if LLM call/validation fails,
    triggering the deterministic question engine.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None

    prompt = (
        f"You are a senior technical interviewer conducting an interview for the role of {target_role}.\n"
        f"Difficulty: {difficulty}\n"
        f"Previous Question Asked: {previous_question}\n"
        f"Candidate's Response: {previous_answer}\n"
        f"Observed Weakness: {observed_weakness or 'None'}\n"
        f"Candidate Core Skills: {', '.join(candidate_skills or [])}\n\n"
        f"Generate the most appropriate next interview question.\n"
        f"Requirements:\n"
        f"1. Directly reference or probe the previous response or candidate's trade-offs.\n"
        f"2. Return ONLY valid JSON in the following exact format without markdown block wrappers:\n"
        f'{{\n'
        f'  "question": "rephrased or follow-up question text",\n'
        f'  "question_type": "technical_followup",\n'
        f'  "topic": "topic name",\n'
        f'  "difficulty": "{difficulty}",\n'
        f'  "reason": "explanation of why this question follows",\n'
        f'  "expected_focus": ["key concept 1", "key concept 2"]\n'
        f'}}\n'
    )

    try:
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
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
        logger.warning("LLM adaptive question generation fallback to deterministic engine: %s", exc)
        return None

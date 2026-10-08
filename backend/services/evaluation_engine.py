import os
import re
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
import httpx
from pydantic import ValidationError

from backend.config import LLM_CONFIG, GEMINI_MODEL
from backend.schemas.schemas import DimensionEvaluation
from backend.services.scoring_engine import evaluate_rubric_for_answer

logger = logging.getLogger(__name__)

# In-memory deterministic cache keyed by SHA256 of inputs + prompt version
_EVALUATION_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_input_hash(
    transcript: str,
    question_text: str,
    category: str,
    resume_skills: Optional[List[str]]
) -> str:
    payload = [
        transcript.strip(),
        question_text.strip(),
        category.strip(),
        sorted(resume_skills or []),
        LLM_CONFIG.get("prompt_version", "v1.0")
    ]
    return hashlib.sha256(json.dumps(payload).encode("utf-8")).hexdigest()


def _verify_evidence_grounding(evidence_list: List[str], transcript: str) -> bool:
    """
    Grounding check: Any quoted text within evidence must appear as a substring in transcript.
    """
    lower_transcript = transcript.lower()
    for ev in evidence_list:
        quotes = re.findall(r'["\']([^"\']{3,})["\']', ev)
        for quote in quotes:
            if quote.lower() not in lower_transcript:
                logger.warning("Grounding check failed: '%s' not found in candidate transcript", quote)
                return False
    return True


def _build_evaluation_prompt(
    transcript: str,
    question_text: str,
    category: str,
    resume_skills: Optional[List[str]]
) -> str:
    skills_context = ", ".join(resume_skills) if resume_skills else "None provided"
    return f"""You are a rigorous but fair technical interviewer.
Evaluate only the evidence contained in the candidate's answer and known interview context.
Do not assume knowledge that the candidate did not demonstrate.
Do not reward keywords merely because they were mentioned.
Do not invent missing project details.
When criticizing an answer, identify the exact gap and explain why it matters.
When recommending improvement, give a concrete next step.
When the answer is strong, explain specifically what made it strong.
Use natural professional language. Do not sound like an automated grading system. Do not repeat generic advice. Do not overpraise or inflate scores.
Your goal is to help the candidate understand what a real interviewer would have thought after hearing this answer.

CRITICAL INSTRUCTION: Any direct quotes included in your evidence strings MUST be exact substring quotes from the candidate's actual answer.

Question: {question_text}
Interview Track: {category}
Candidate Declared Skills: {skills_context}

Candidate Answer:
\"\"\"{transcript}\"\"\"

Respond with valid JSON matching this exact structure:
{{
  "overall_assessment": "<1-2 sentence human interviewer perspective on what was demonstrated>",
  "what_went_well": ["<concrete strength 1 grounded in specific answer text>"],
  "what_was_missing": ["<Format: 'What happened: ... Why it matters: ... What to do next: ...'>"],
  "dimensions": {{
    "structure": {{
      "score": <0-100 float>,
      "evidence": ["<concrete facts e.g. sentence count, transitions, word count>"],
      "explanation": "<rationale for score>",
      "recommended_action": "<concrete improvement suggestion>"
    }},
    "technical": {{
      "score": <0-100 float>,
      "evidence": ["<specific domain concepts or keywords observed>"],
      "explanation": "<rationale>",
      "recommended_action": "<suggestion>"
    }},
    "reasoning": {{
      "score": <0-100 float>,
      "evidence": ["<trade-off or causal markers observed>"],
      "explanation": "<rationale>",
      "recommended_action": "<suggestion>"
    }},
    "star": {{
      "score": <0-100 float>,
      "evidence": ["<presence of situation, task, action, result with metrics>"],
      "explanation": "<rationale>",
      "recommended_action": "<suggestion>"
    }},
    "consistency": {{
      "score": <0-100 float>,
      "evidence": ["<matching skills or experience alignment>"],
      "explanation": "<rationale>",
      "recommended_action": "<suggestion>"
    }}
  }},
  "missing_concepts": ["<concept 1>", "<concept 2>"]
}}"""


def _call_gemini(prompt: str, api_key: str) -> Optional[dict]:
    model = GEMINI_MODEL or "gemini-flash-lite-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": LLM_CONFIG.get("temperature", 0.0),
            "responseMimeType": "application/json"
        }
    }
    for attempt in range(LLM_CONFIG.get("max_retries", 0) + 1):
        try:
            with httpx.Client(timeout=LLM_CONFIG.get("timeout_seconds", 2.0)) as client:
                res = client.post(url, headers=headers, json=body)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return json.loads(text_content)
        except Exception as e:
            logger.warning("Gemini attempt %d error: %s", attempt + 1, e)
            break
    return None


def _call_openai(prompt: str, api_key: str) -> Optional[dict]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an expert technical interviewer evaluating an interview response. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": LLM_CONFIG.get("temperature", 0.0),
        "response_format": {"type": "json_object"}
    }
    for attempt in range(LLM_CONFIG.get("max_retries", 1) + 1):
        try:
            with httpx.Client(timeout=LLM_CONFIG.get("timeout_seconds", 5.0)) as client:
                res = client.post(url, headers=headers, json=body)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return json.loads(content)
        except Exception as e:
            logger.warning("OpenAI attempt %d error: %s", attempt + 1, e)
    return None


def _validate_and_format_llm_response(
    raw_data: dict,
    transcript: str,
    category: str,
    resume_skills: Optional[List[str]]
) -> Optional[Dict[str, Any]]:
    try:
        dimensions = {}
        required = ["structure", "technical", "reasoning", "star", "consistency"]
        raw_dims = raw_data.get("dimensions", raw_data)

        for dim in required:
            if dim not in raw_dims:
                logger.warning("LLM response missing dimension: %s", dim)
                return None
            parsed_dim = DimensionEvaluation(**raw_dims[dim])
            # Grounding check
            if not _verify_evidence_grounding(parsed_dim.evidence, transcript):
                return None
            dimensions[dim] = parsed_dim.model_dump()

        # Compute overall score from validated dimensions
        struct_s = dimensions["structure"]["score"]
        tech_s = dimensions["technical"]["score"]
        reas_s = dimensions["reasoning"]["score"]
        star_s = dimensions["star"]["score"]
        cons_s = dimensions["consistency"]["score"]

        if category.lower() == "technical":
            overall_score = round(0.35 * tech_s + 0.25 * reas_s + 0.20 * struct_s + 0.20 * cons_s, 1)
        elif category.lower() in ["behavioral", "hr", "pressure"]:
            overall_score = round(0.35 * star_s + 0.25 * reas_s + 0.25 * struct_s + 0.15 * cons_s, 1)
        else:
            overall_score = round((struct_s + tech_s + reas_s + star_s + cons_s) / 5.0, 1)

        strengths = raw_data.get("what_went_well") or [d["explanation"] for d in dimensions.values() if d["score"] >= 70.0] or ["Answer was submitted."]
        weaknesses = [d["explanation"] for d in dimensions.values() if d["score"] < 70.0] or ["Could provide more operational metrics."]
        what_was_missing = raw_data.get("what_was_missing") or weaknesses
        overall_assessment = raw_data.get("overall_assessment") or (
            "Clear technical response with actionable context." if overall_score >= 70 else
            "Response demonstrates foundational understanding, but lacks operational depth."
        )
        suggestions = [d["recommended_action"] for d in dimensions.values() if d["score"] < 75.0] or ["Continue practicing structured responses."]

        return {
            "score": overall_score,
            "overall_score": overall_score,
            "structure_score": struct_s,
            "clarity_score": struct_s,
            "depth_score": tech_s,
            "technical_score": tech_s,
            "reasoning_score": reas_s,
            "star_score": star_s,
            "consistency_score": cons_s,
            "dimensions": dimensions,
            "structure": dimensions["structure"],
            "technical": dimensions["technical"],
            "reasoning": dimensions["reasoning"],
            "star": dimensions["star"],
            "consistency": dimensions["consistency"],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "what_went_well": strengths,
            "what_was_missing": what_was_missing,
            "overall_assessment": overall_assessment,
            "missing_concepts": raw_data.get("missing_concepts", ["Operational metrics", "Edge cases"]),
            "suggestions": suggestions,
            "prompt_version": LLM_CONFIG.get("prompt_version", "v1.0")
        }
    except (ValidationError, Exception) as e:
        logger.warning("LLM response validation failed: %s", e)
        return None


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
    Evaluates candidate answer.
    Checks GEMINI_API_KEY, then OPENAI_API_KEY, validating output and grounding.
    Falls back to deterministic rubric when no keys are configured or when calls fail/time out.
    """
    text = (transcript or "").strip()

    # Deterministic input caching
    cache_key = _get_input_hash(text, question_text, category, resume_skills)
    if cache_key in _EVALUATION_CACHE:
        logger.info("Evaluation cache hit for key %s", cache_key[:8])
        return _EVALUATION_CACHE[cache_key]

    # Evidence gate: empty or trivial non-answers must NOT be sent to LLM
    words = text.split()
    lower_text = text.lower()
    TRIVIAL_NON_ANSWERS = {
        "idk", "i don't know", "idk.", "no", "yes", "skip", "none", "pass", "na", "n/a",
        "dsjnd", "test", "asdf", "hello", "hi", "bye", "ok", "okay"
    }
    if len(words) == 0 or len(words) < 4 or lower_text in TRIVIAL_NON_ANSWERS:
        result = evaluate_rubric_for_answer(
            transcript=transcript,
            question_text=question_text,
            category=category,
            resume_skills=resume_skills,
            response_time=response_time,
            wpm=wpm,
            filler_count=filler_count
        )
        result["engine_used"] = "rubric_evidence_gate"
        result["prompt_version"] = LLM_CONFIG.get("prompt_version", "v1.0")
        _EVALUATION_CACHE[cache_key] = result
        return result

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key or openai_key:
        prompt = _build_evaluation_prompt(text, question_text, category, resume_skills)
        raw_llm = None
        engine_used = None

        if gemini_key:
            logger.info("Attempting evaluation with Gemini provider...")
            raw_llm = _call_gemini(prompt, gemini_key)
            if raw_llm:
                engine_used = "llm_gemini"

        if not raw_llm and openai_key:
            logger.info("Attempting evaluation with OpenAI provider...")
            raw_llm = _call_openai(prompt, openai_key)
            if raw_llm:
                engine_used = "llm_openai"

        if raw_llm:
            formatted = _validate_and_format_llm_response(raw_llm, text, category, resume_skills)
            if formatted:
                formatted["engine_used"] = engine_used
                _EVALUATION_CACHE[cache_key] = formatted
                return formatted
            else:
                logger.warning("LLM output rejected by validation or grounding check. Falling back to deterministic rubric.")

    # Offline deterministic fallback
    result = evaluate_rubric_for_answer(
        transcript=transcript,
        question_text=question_text,
        category=category,
        resume_skills=resume_skills,
        response_time=response_time,
        wpm=wpm,
        filler_count=filler_count
    )
    result["engine_used"] = "rubric"
    result["prompt_version"] = LLM_CONFIG.get("prompt_version", "v1.0")
    _EVALUATION_CACHE[cache_key] = result
    return result
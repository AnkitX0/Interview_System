"""
backend/services/llm_gemini_service.py
Structured Multi-Task Gemini LLM Intelligence Provider.
Handles:
1. Resume Understanding & Grounded Claim Extraction
2. Adaptive Question Strategy Decision
3. Qualitative Answer Evaluation & Evasion Detection
4. Final Assessment Synthesis & Explanations
Fully validated with Pydantic with seamless fallback to deterministic engines.
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("interview_system.llm_gemini")


# -------------------------
# Pydantic Output Schemas
# -------------------------
class LLMQuestionDecision(BaseModel):
    continue_interview: bool = True
    question: str
    question_type: str = "FOLLOW_UP"
    topic: str = "system_architecture"
    resume_claim_reference: Optional[str] = None
    reason: str = "Contextual follow-up probing technical mechanism and evidence."
    depth_level: int = 2
    expected_evidence: List[str] = Field(default_factory=list)


class LLMExtractedClaim(BaseModel):
    claim_text: str
    claim_type: str = "performance"
    technology: Optional[str] = None
    metric: Optional[str] = None
    probe_priority: float = 0.8
    possible_questions: List[str] = Field(default_factory=list)


class LLMResumeAnalysis(BaseModel):
    candidate_summary: str = ""
    core_skills: List[str] = Field(default_factory=list)
    claims: List[LLMExtractedClaim] = Field(default_factory=list)


class LLMAnswerQualitative(BaseModel):
    answered_question: bool = True
    candidate_diversion: bool = False
    technical_depth: str = "adequate"
    missing_information: Optional[str] = None
    recommended_probe: Optional[str] = None


class LLMReportInsights(BaseModel):
    why_this_score: str
    what_went_well: List[str] = Field(default_factory=list)
    what_held_you_back: List[str] = Field(default_factory=list)
    next_practice_recommendation: str = "Technical Claim Defense & Performance Measurement"


# -------------------------
# Core Robust Gemini Client
# -------------------------
def call_gemini_json(prompt: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Calls Google Generative Language API with JSON response enforcement.
    Tries configured GEMINI_MODEL with tight 2.0s timeout.
    Returns parsed JSON dictionary or None for immediate deterministic fallback.
    """
    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    primary_model = GEMINI_MODEL or "gemini-flash-lite-latest"
    models = [primary_model]
    if primary_model != "gemini-flash-lite-latest":
        models.append("gemini-flash-lite-latest")

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600,
                "responseMimeType": "application/json",
            },
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    continue
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    continue

                raw_text = parts[0].get("text", "").strip()
                # Clean Markdown code block wrapper if present
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)

                return json.loads(raw_text)
        except urllib.error.HTTPError as http_err:
            logger.warning("Gemini HTTP %s on model %s", http_err.code, model)
            continue
        except Exception as exc:
            logger.warning("Gemini call exception on model %s: %s", model, exc)
            break

    return None


# -------------------------
# Task 1: Question Strategist
# -------------------------
def decide_llm_question_strategy(
    target_role: str,
    difficulty: str,
    interview_state: str,
    previous_question: str,
    previous_answer: str,
    previous_evaluation: Optional[Dict[str, Any]] = None,
    unresolved_points: Optional[List[Dict[str, Any]]] = None,
    resume_claims: Optional[List[str]] = None,
    questions_already_asked: Optional[List[str]] = None,
    topics_covered: Optional[List[str]] = None,
    current_depth: int = 2,
    remaining_budget_hint: str = "Adaptive",
) -> Optional[LLMQuestionDecision]:
    """
    Decides the strategic next interview question based on interview memory.
    """
    unresolved_str = (
        "; ".join([u.get("unresolved_point", "") for u in (unresolved_points or []) if isinstance(u, dict)])
        if unresolved_points else "None"
    )
    claims_str = "; ".join((resume_claims or [])[:4]) if resume_claims else "None"
    already_asked_str = "; ".join([q[:60] for q in (questions_already_asked or [])[-5:]])

    system_prompt = (
        f"You are conducting a realistic professional technical interview for a {target_role} ({difficulty} level).\n"
        f"Interview State: {interview_state} (Current Depth Ladder: Level {current_depth}/8)\n"
        f"Candidate Resume Claims: {claims_str}\n"
        f"Previous Question: {previous_question}\n"
        f"Candidate's Answer: {previous_answer}\n"
        f"Unresolved Points / Evasions: {unresolved_str}\n"
        f"Questions Already Asked: {already_asked_str}\n"
        f"Topics Covered So Far: {', '.join(topics_covered or [])}\n\n"
        "Instructions for Question Strategist:\n"
        "1. Ask exactly ONE professional question.\n"
        "2. Priority 1: If the candidate avoided the previous question or left claims unresolved, directly return to the unresolved issue.\n"
        "3. Priority 2: If the candidate made a concrete resume claim, ask how they measured or implemented it.\n"
        "4. Priority 3: If previous answer was technically strong, increase depth to trade-offs, 10x scaling, or failure recovery.\n"
        "5. Do NOT praise the candidate unnecessarily. Do NOT repeat questions already asked.\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        '  "continue_interview": true,\n'
        '  "question": "question text",\n'
        '  "question_type": "FOLLOW_UP",\n'
        '  "topic": "topic_name",\n'
        '  "resume_claim_reference": "optional claim referenced",\n'
        '  "reason": "why this question follows",\n'
        '  "depth_level": 3,\n'
        '  "expected_evidence": ["metric baseline", "tooling", "architecture"]\n'
        "}"
    )

    result_json = call_gemini_json(system_prompt, timeout=8)
    if result_json:
        try:
            return LLMQuestionDecision(**result_json)
        except Exception as e:
            logger.warning("LLMQuestionDecision validation error: %s", e)
    return None


# -------------------------
# Task 2: Resume Understanding & Claim Extraction
# -------------------------
def analyze_resume_with_gemini(resume_text: str) -> Optional[LLMResumeAnalysis]:
    """
    Extracts structured, grounded claims and metrics from candidate resume text.
    Strictly forbids hallucinating or inventing claims not in the text.
    """
    bounded_text = resume_text[:3500]
    prompt = (
        "You are an expert technical interviewer reviewing a candidate's resume.\n"
        "Analyze the following resume and extract verifiable technical claims, performance improvements, "
        "and architectural decisions. DO NOT hallucinate facts not present in the text.\n\n"
        f"Resume Text:\n{bounded_text}\n\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "candidate_summary": "1-2 sentence overview",\n'
        '  "core_skills": ["Python", "PostgreSQL", "FastAPI"],\n'
        '  "claims": [\n'
        "    {\n"
        '      "claim_text": "Reduced API response time by 35% through query optimization",\n'
        '      "claim_type": "performance",\n'
        '      "technology": "PostgreSQL",\n'
        '      "metric": "35%",\n'
        '      "probe_priority": 0.85,\n'
        '      "possible_questions": ["How did you identify the queries as the bottleneck?"]\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    result_json = call_gemini_json(prompt, timeout=10)
    if result_json:
        try:
            return LLMResumeAnalysis(**result_json)
        except Exception as e:
            logger.warning("LLMResumeAnalysis validation error: %s", e)
    return None


# -------------------------
# Task 3: Answer Qualitative Evaluation & Evasion Detection
# -------------------------
def evaluate_answer_qualitative_gemini(
    question_text: str,
    answer_text: str,
    target_role: str,
) -> Optional[LLMAnswerQualitative]:
    """
    Qualitatively assesses whether the candidate directly answered the question
    or diverted to adjacent concepts without providing requested evidence.
    """
    prompt = (
        f"Role: {target_role}\n"
        f"Interviewer Question: {question_text}\n"
        f"Candidate Answer: {answer_text}\n\n"
        "Evaluate whether the candidate directly answered the question asked.\n"
        "Specifically check:\n"
        "- Did the candidate divert to naming technologies without addressing the actual question (e.g., measurement, mechanism)?\n"
        "- What specific evidence was missing?\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "answered_question": true,\n'
        '  "candidate_diversion": false,\n'
        '  "technical_depth": "shallow/adequate/deep",\n'
        '  "missing_information": "description of missing details or null",\n'
        '  "recommended_probe": "suggested follow-up probe"\n'
        "}"
    )

    result_json = call_gemini_json(prompt, timeout=6)
    if result_json:
        try:
            return LLMAnswerQualitative(**result_json)
        except Exception as e:
            logger.warning("LLMAnswerQualitative validation error: %s", e)
    return None


# -------------------------
# Task 4: Final Report Qualitative Insights
# -------------------------
def synthesize_report_insights_gemini(
    target_role: str,
    score: float,
    strengths: List[str],
    weaknesses: List[str],
    unresolved_claims: List[str],
) -> Optional[LLMReportInsights]:
    """
    Synthesizes actionable, evidence-based report commentary explaining
    why the preparation score was earned and specific next practice areas.
    """
    prompt = (
        f"Candidate Target Role: {target_role}\n"
        f"Overall Preparation Score: {score:.1f}/100\n"
        f"Observed Strengths: {', '.join(strengths[:4])}\n"
        f"Observed Weaknesses: {', '.join(weaknesses[:4])}\n"
        f"Unresolved Claims / Evasions: {', '.join(unresolved_claims[:3]) if unresolved_claims else 'None'}\n\n"
        "Write an honest, professional interview preparation assessment.\n"
        "Explain WHY this score was earned based on evidence.\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "why_this_score": "Concise paragraph explaining the score grounded in demonstrated depth.",\n'
        '  "what_went_well": ["Bullet 1", "Bullet 2"],\n'
        '  "what_held_you_back": ["Bullet 1", "Bullet 2"],\n'
        '  "next_practice_recommendation": "Specific practice recommendation (e.g. Defending Performance Claims)"\n'
        "}"
    )

    result_json = call_gemini_json(prompt, timeout=8)
    if result_json:
        try:
            return LLMReportInsights(**result_json)
        except Exception as e:
            logger.warning("LLMReportInsights validation error: %s", e)
    return None

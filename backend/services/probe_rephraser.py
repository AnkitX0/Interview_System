"""
backend/services/probe_rephraser.py
Optional LLM phrasing for probe ladder questions with strict claim grounding,
banned-word protection, timeout guards, and deterministic fallback.
"""

import os
import re
import json
import hashlib
import logging
from typing import Dict, Optional, List
import httpx

logger = logging.getLogger(__name__)

# In-memory cache for rephrased probes (keyed by sha256 of stage + claim + template)
_PROBE_CACHE: Dict[str, str] = {}

BANNED_PROBE_REGEX = re.compile(
    r"\b(bluff|lie|lies|fake|dishonest|impostor|fraud|stupid|incompetent|prove yourself)\b",
    re.IGNORECASE
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "from", "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "that", "this", "these", "those",
    "is", "was", "are", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "will", "would", "should", "your",
    "our", "my", "using", "used", "which", "where", "when", "why", "how"
}


def _extract_grounding_tokens(claim_text: str) -> List[str]:
    """Extracts significant domain tokens (length >= 3, not stopwords) from claim text."""
    words = re.findall(r"\b[A-Za-z0-9_+#.-]+\b", claim_text.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def verify_probe_grounding(rephrased_text: str, claim_text: str) -> bool:
    """
    Strict claim grounding verification.
    The rephrased question MUST reference at least one significant entity or domain token
    present in the original resume claim.
    """
    tokens = _extract_grounding_tokens(claim_text)
    if not tokens:
        return True  # If claim had no extractable tokens, pass through

    lower_rephrased = rephrased_text.lower()
    return any(tok in lower_rephrased for tok in tokens)


def _call_gemini_rephrase(
    prompt: str,
    api_key: str,
    timeout: float
) -> Optional[str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 100}
    }
    with httpx.Client(timeout=timeout) as client:
        res = client.post(url, json=payload)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    return None


def _call_openai_rephrase(
    prompt: str,
    api_key: str,
    timeout: float
) -> Optional[str]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional technical interviewer. Output only the rephrased question with no markdown or formatting."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 100
    }
    with httpx.Client(timeout=timeout) as client:
        res = client.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            data = res.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    return None


def rephrase_probe_question(
    claim_text: str,
    stage: str,
    fallback_template_text: str,
    timeout: float = 2.5
) -> str:
    """
    Optionally rephrases a deterministic probe template using an LLM.
    Strictly guarantees:
    1. Returns fallback_template_text if no provider is configured.
    2. Returns fallback_template_text if call times out or errors.
    3. Returns fallback_template_text if rephrased text contains banned hostile terms.
    4. Returns fallback_template_text if rephrased text fails strict claim grounding.
    5. Caches successful rephrasings in-memory.
    """
    clean_claim = (claim_text or "").strip()
    clean_fallback = (fallback_template_text or "").strip()
    if not clean_claim or not clean_fallback:
        return clean_fallback

    # Cache lookup
    cache_key = hashlib.sha256(f"{stage}:{clean_claim}:{clean_fallback}".encode("utf-8")).hexdigest()
    if cache_key in _PROBE_CACHE:
        return _PROBE_CACHE[cache_key]

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not gemini_key and not openai_key:
        return clean_fallback

    prompt = (
        f"You are a technical interviewer conducting a structured technical interview.\n"
        f"The candidate's resume claim is: '{clean_claim}'.\n"
        f"The interview stage is: '{stage}'.\n"
        f"The template question is: '{clean_fallback}'.\n\n"
        f"Rephrase this template question into a natural, direct interview question.\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"1. You MUST directly preserve and reference the specific tools, metrics, or technologies from the claim: '{clean_claim}'.\n"
        f"2. Never use confrontational or hostile language (no words like bluff, lie, fake, prove).\n"
        f"3. Return ONLY the single rephrased question without quotes or preamble."
    )

    rephrased = None
    try:
        if gemini_key:
            rephrased = _call_gemini_rephrase(prompt, gemini_key, timeout)
        elif openai_key:
            rephrased = _call_openai_rephrase(prompt, openai_key, timeout)
    except Exception as exc:
        logger.warning("LLM probe rephrasing call failed (%s); using deterministic template.", exc)
        return clean_fallback

    if not rephrased:
        return clean_fallback

    # Clean whitespace and surrounding quotes
    rephrased = rephrased.strip().strip('"\'`')

    # Banned words check
    if BANNED_PROBE_REGEX.search(rephrased):
        logger.warning("LLM rephrased probe contained banned hostile terms; falling back to template.")
        return clean_fallback

    # Strict grounding check
    if not verify_probe_grounding(rephrased, clean_claim):
        logger.warning(
            "LLM rephrased probe failed claim grounding (did not reference claim '%s'); falling back to template.",
            clean_claim
        )
        return clean_fallback

    # Ensure ends with question mark
    if not rephrased.endswith("?"):
        rephrased += "?"

    _PROBE_CACHE[cache_key] = rephrased
    return rephrased


def clear_probe_cache() -> None:
    """Clears in-memory probe rephrasing cache (used in tests)."""
    _PROBE_CACHE.clear()

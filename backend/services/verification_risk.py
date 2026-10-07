"""
backend/services/verification_risk.py
Deterministic Verification Risk evaluation engine.

Evaluates response transcripts for observable verification-risk wording patterns:
- Generic-phrase density
- Buzzword density vs concrete specifics (metrics, tools, concrete verbs)
- Lack of specifics
- Repetition with earlier answers (no new information)
- Ownership vagueness

Guards:
- Responses below minimum word count return 'not_computed' (does not penalize brevity).
- Never penalizes accents, grammar, or disfluency.
- Strictly observable heuristics; does not claim honesty or deception.
"""

import re
from typing import Dict, Any, List, Optional
from backend.config import VERIFICATION_RISK_CONFIG


# Standard technology keywords for specifics detection
KNOWN_TECH_SPECIFICS = {
    "redis", "postgres", "postgresql", "mysql", "mongodb", "cassandra", "dynamodb",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "kafka", "rabbitmq",
    "grpc", "graphql", "rest", "fastapi", "flask", "django", "react", "vue", "next.js",
    "nginx", "aws", "gcp", "azure", "s3", "ec2", "sqs", "sns", "prometheus", "grafana",
    "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "git", "ci/cd",
    "btree", "sharding", "replication", "indexing", "partitioning", "concurrency",
    "threadpool", "goroutine", "mutex", "websocket", "http/2", "jwt", "oauth"
}


def _extract_tokens(text: str) -> List[str]:
    return [w for w in re.findall(r"\b[a-zA-Z0-9_\-+#.]+\b", text.lower())]


def compute_verification_risk(
    transcript: str,
    previous_answers: Optional[List[str]] = None,
    resume_context: Optional[Dict[str, Any]] = None,
    question_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes deterministic verification risk for an answer response.
    Returns:
        {
            "score": float (0-100) or None,
            "level": "low" | "moderate" | "elevated" | "not_computed",
            "evidence": List[str],
            "explanation": str,
            "recommended_action": str,
            "disclaimer": str
        }
    """
    config = VERIFICATION_RISK_CONFIG
    disclaimer = config["disclaimer"]
    min_words = config["min_word_count"]

    tokens = _extract_tokens(transcript or "")
    word_count = len(tokens)

    # 1. Guard against brief responses
    if word_count < min_words:
        return {
            "score": None,
            "level": "not_computed",
            "evidence": [f"Response has {word_count} words (minimum required is {min_words})."],
            "explanation": f"Verification risk was not computed because the answer length ({word_count} words) is below the minimum threshold of {min_words} words.",
            "recommended_action": "Provide a comprehensive answer with concrete implementation details.",
            "disclaimer": disclaimer,
        }

    lower_text = (transcript or "").lower()
    weights = config["weights"]
    evidence: List[str] = []

    # 2. Signal 1: Generic phrasing density
    generic_matches = [
        phrase for phrase in config["generic_phrases"]
        if phrase in lower_text
    ]
    generic_score = min(1.0, len(generic_matches) * 0.4)
    if generic_matches:
        evidence.append(f"Contains generic phrasing ({len(generic_matches)} detected: {', '.join(repr(m) for m in generic_matches[:2])}).")

    # 3. Signal 2 & 3: Buzzwords vs Concrete Specifics & Lack of Specifics
    buzzword_matches = [
        bw for bw in config["buzzwords"]
        if re.search(rf"\b{re.escape(bw)}\b", lower_text)
    ]
    
    # Concrete numbers & metrics
    metric_matches = re.findall(r"\b\d+(\.\d+)?%?|\b\d+(?:ms|s|m|k|mb|gb|tb|rps|qps)\b", lower_text)
    metric_count = len(metric_matches)

    # Named tech tools
    tech_matches = [
        tech for tech in KNOWN_TECH_SPECIFICS
        if re.search(rf"\b{re.escape(tech)}\b", lower_text)
    ]

    # Concrete action verbs
    verb_matches = [
        verb for verb in config["concrete_verbs"]
        if re.search(rf"\b{re.escape(verb)}\b", lower_text)
    ]

    total_specifics = metric_count + len(tech_matches) + len(verb_matches)
    buzzword_count = len(buzzword_matches)

    # Buzzwords vs Specifics
    if buzzword_count > 0 and total_specifics == 0:
        buzzword_score = 1.0
        evidence.append(f"Buzzword density ({buzzword_count}) without concrete technical specifics.")
    elif buzzword_count > total_specifics:
        buzzword_score = min(1.0, (buzzword_count - total_specifics) / max(1, buzzword_count) + 0.3)
        evidence.append(f"Buzzword density ({buzzword_count}) exceeds concrete technical specifics ({total_specifics}).")
    elif buzzword_count > 0:
        buzzword_score = 0.2
    else:
        buzzword_score = 0.0

    # Lack of specifics
    if total_specifics == 0:
        lack_specifics_score = 1.0
        evidence.append("No concrete metrics, named technologies, or specific mechanisms identified.")
    elif total_specifics <= 2:
        lack_specifics_score = 0.45
        evidence.append(f"Limited technical specifics ({total_specifics} identified).")
    else:
        lack_specifics_score = 0.0
        sample_specifics = (tech_matches[:2] + verb_matches[:2])
        if sample_specifics:
            evidence.append(f"Concrete technical specifics cited: {', '.join(sample_specifics)}.")

    # 4. Signal 4: Repetition check against prior answers
    repetition_score = 0.0
    if previous_answers:
        curr_meaningful = {w for w in tokens if len(w) > 3}
        if curr_meaningful:
            max_overlap = 0.0
            for prev_ans in previous_answers:
                prev_tokens = {w for w in _extract_tokens(prev_ans) if len(w) > 3}
                if prev_tokens:
                    overlap_ratio = len(curr_meaningful & prev_tokens) / len(curr_meaningful)
                    if overlap_ratio > max_overlap:
                        max_overlap = overlap_ratio

            if max_overlap >= 0.65:
                repetition_score = 1.0
                evidence.append(f"High repetition ({int(max_overlap * 100)}% vocabulary overlap) with preceding response without novel technical detail.")
            elif max_overlap >= 0.40:
                repetition_score = 0.5
                evidence.append(f"Moderate vocabulary overlap ({int(max_overlap * 100)}%) with prior response.")

    # 5. Signal 5: Ownership vagueness
    vague_ownership_matches = [
        phrase for phrase in config["vague_ownership_phrases"]
        if phrase in lower_text
    ]
    if vague_ownership_matches:
        ownership_score = 1.0
        evidence.append(f"Vague ownership phrasing observed: {repr(vague_ownership_matches[0])}.")
    else:
        ownership_score = 0.0

    # Weighted calculation normalized by active components
    active_weights = {
        "generic_phrases": weights["generic_phrases"],
        "buzzwords_vs_specifics": weights["buzzwords_vs_specifics"],
        "lack_of_specifics": weights["lack_of_specifics"],
        "ownership_vagueness": weights["ownership_vagueness"],
    }
    signals = {
        "generic_phrases": generic_score,
        "buzzwords_vs_specifics": buzzword_score,
        "lack_of_specifics": lack_specifics_score,
        "ownership_vagueness": ownership_score,
    }
    if previous_answers:
        active_weights["repetition"] = weights["repetition"]
        signals["repetition"] = repetition_score

    sum_weights = sum(active_weights.values())
    weighted_sum = sum(signals[k] * active_weights[k] for k in active_weights) / sum_weights
    final_score = round(min(100.0, max(0.0, weighted_sum * 100.0)), 1)


    thresholds = config["thresholds"]
    if final_score <= thresholds["low_max"]:
        level = "low"
        explanation = "Response provides concrete technical specifics and clear implementation details with low verification risk."
        action = "Maintain technical precision and quantified outcomes across system explanations."
    elif final_score <= thresholds["moderate_max"]:
        level = "moderate"
        explanation = "Response includes partial specifics but contains generalized terminology that would benefit from concrete validation."
        action = "Anchor architectural choices in specific technologies, performance metrics, and individual contributions."
    else:
        level = "elevated"
        explanation = "Response relies substantially on high-level buzzwords and generalized phrasing without concrete mechanisms or clear ownership."
        action = "Specify exact tools, architectural trade-offs, and measurable engineering outcomes (e.g., latency, throughput, scale)."

    return {
        "score": final_score,
        "level": level,
        "evidence": evidence,
        "explanation": explanation,
        "recommended_action": action,
        "disclaimer": disclaimer,
    }

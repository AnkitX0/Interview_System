import re
from typing import Dict, Any, List, Optional
from backend.config import DEFAULT_SESSION_WEIGHTS, WORD_COUNT_BANDS, FILLER_WORDS

TECHNICAL_KEYWORDS = [
    "api", "rest", "database", "sql", "nosql", "index", "cache", "redis",
    "architecture", "latency", "throughput", "microservices", "docker", "kubernetes",
    "acid", "transaction", "asynchronous", "concurrency", "thread", "process",
    "security", "jwt", "auth", "scaling", "load balancer", "sharding", "algorithm",
    "complexity", "o(n)", "memory", "cpu", "middleware", "framework", "schema"
]

STAR_MARKERS = {
    "situation": ["when", "during", "at my previous", "in my project", "the scenario was", "context"],
    "task": ["my role was", "tasked with", "goal was", "objective was", "needed to", "responsible for"],
    "action": ["i implemented", "i designed", "i created", "i built", "i analyzed", "i solved", "i refactored", "i decided"],
    "result": ["resulting in", "increased", "decreased", "improved", "reduced", "delivered", "outcome was", "achieved", "%"]
}

REASONING_MARKERS = [
    "because", "therefore", "tradeoff", "as a result", "in order to", "instead of",
    "the reason being", "we chose", "this enabled", "compared to", "alternative"
]


def evaluate_rubric_for_answer(
    transcript: str,
    question_text: str = "",
    category: str = "Technical",
    resume_skills: Optional[List[str]] = None,
    response_time: float = 0.0,
    wpm: float = 0.0,
    filler_count: int = 0
) -> Dict[str, Any]:
    """
    Evaluates an interview answer using a structured, transparent rubric:
    1. Structure (0-100)
    2. Technical depth (0-100)
    3. Reasoning (0-100)
    4. STAR quality (0-100)
    5. Resume consistency (0-100)
    6. Overall answer quality (0-100)
    """
    text = (transcript or "").strip()
    words = text.split()
    word_count = len(words)
    lower_text = text.lower()

    if word_count < WORD_COUNT_BANDS["floor_min"]:
        empty_dimensions = {
            "structure": {
                "score": 20.0,
                "evidence": [f"{word_count} words submitted (minimum expected: {WORD_COUNT_BANDS['floor_min']})", "0 sentence transitions"],
                "explanation": "Answer is too brief or empty to assess narrative flow.",
                "recommended_action": "Provide a complete verbal or written response of at least 70 words."
            },
            "technical": {
                "score": 15.0,
                "evidence": ["0 domain keywords found", f"Evaluated category: {category}"],
                "explanation": "No technical concepts or mechanisms were provided.",
                "recommended_action": "Describe specific tools, frameworks, protocols, and architectural patterns."
            },
            "reasoning": {
                "score": 15.0,
                "evidence": ["trade-off terms: 0", "No causal justification markers found"],
                "explanation": "No rationale or comparative trade-offs were detected.",
                "recommended_action": "Articulate why an engineering decision was made and compare against alternatives."
            },
            "star": {
                "score": 10.0,
                "evidence": ["0/4 STAR components identified", "0 quantified results found"],
                "explanation": "No STAR elements (Situation, Task, Action, Result) detected in response.",
                "recommended_action": "Use the STAR method: Situation, Task, Action, and measurable Result."
            },
            "consistency": {
                "score": 50.0,
                "evidence": ["Insufficient text to cross-reference against resume skills"],
                "explanation": "Could not verify background claims from an empty or single-word answer.",
                "recommended_action": "Reference specific project experiences from your background."
            }
        }
        return {
            "score": 20.0,
            "overall_score": 20.0,
            "structure_score": 20.0,
            "clarity_score": 20.0,
            "depth_score": 15.0,
            "technical_score": 15.0,
            "reasoning_score": 15.0,
            "star_score": 10.0,
            "consistency_score": 50.0,
            "dimensions": empty_dimensions,
            "structure": empty_dimensions["structure"],
            "technical": empty_dimensions["technical"],
            "reasoning": empty_dimensions["reasoning"],
            "star": empty_dimensions["star"],
            "consistency": empty_dimensions["consistency"],
            "strengths": ["Answer was submitted."],
            "weaknesses": ["Answer is too brief or empty to assess meaningfully."],
            "missing_concepts": ["Detailed explanation", "Concrete examples"],
            "suggestions": ["Elaborate on your thought process with specific technical mechanisms and personal experience."]
        }

    # 1. Structure Score (0 - 100)
    # Rewards appropriate length (60-250 words), sentence transitions, punctuation
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = len(sentences)
    length_factor = min(1.0, word_count / float(WORD_COUNT_BANDS["optimal_min"]))
    structure_bonus = 20.0 if sentence_count >= 3 else 10.0
    transitions = sum(1 for w in ["first", "second", "additionally", "furthermore", "finally", "specifically", "overall"] if w in lower_text)
    transition_bonus = min(20.0, transitions * 7.0)
    structure_score = round(min(95.0, max(35.0, (length_factor * 55.0) + structure_bonus + transition_bonus)), 1)

    # 2. Technical Depth Score (0 - 100)
    matched_tech = [k for k in TECHNICAL_KEYWORDS if re.search(r"\b" + re.escape(k) + r"\b", lower_text)]
    if category.lower() in ["technical", "backend", "frontend", "system design"]:
        tech_score = round(min(95.0, max(40.0, 30.0 + (len(matched_tech) * 12.0) + (length_factor * 20.0))), 1)
    else:
        tech_score = round(min(90.0, max(50.0, 50.0 + (len(matched_tech) * 8.0))), 1)

    # 3. Reasoning Score (0 - 100)
    matched_reasoning = [r for r in REASONING_MARKERS if r in lower_text]
    reasoning_score = round(min(95.0, max(35.0, 35.0 + (len(matched_reasoning) * 15.0) + (length_factor * 20.0))), 1)

    # 4. STAR Quality Score (0 - 100)
    star_hits = {
        dim: any(marker in lower_text for marker in markers)
        for dim, markers in STAR_MARKERS.items()
    }
    star_count = sum(1 for present in star_hits.values() if present)
    star_score = round(min(95.0, max(30.0, 25.0 + (star_count * 17.5))), 1)

    # 5. Resume Consistency Score (0 - 100)
    if resume_skills and len(resume_skills) > 0:
        matched_resume = [s for s in resume_skills if s.lower() in lower_text]
        consistency_score = round(min(95.0, max(55.0, 60.0 + (len(matched_resume) * 10.0))), 1)
    else:
        matched_resume = []
        consistency_score = 75.0

    # 6. Overall Score
    if category.lower() == "technical":
        overall_score = round(
            0.35 * tech_score +
            0.25 * reasoning_score +
            0.20 * structure_score +
            0.20 * consistency_score,
            1
        )
    elif category.lower() in ["behavioral", "hr", "pressure"]:
        overall_score = round(
            0.35 * star_score +
            0.25 * reasoning_score +
            0.25 * structure_score +
            0.15 * consistency_score,
            1
        )
    else:
        overall_score = round(
            (structure_score + tech_score + reasoning_score + star_score + consistency_score) / 5.0,
            1
        )

    # Concrete Evidence Generation
    metric_matches = re.findall(
        r"\b\d+%(?!\w)|\b\d+(?:[xXkKmM]|\s*(?:percent|users|requests|ms|seconds|minutes|million|times|gb|mb|tb|queries))\b",
        text,
        re.IGNORECASE
    )
    metric_evidence = (
        f"{len(metric_matches)} quantified metric(s) found ({', '.join(metric_matches[:3])})"
        if metric_matches
        else "0 quantified results found"
    )

    detected_fillers = filler_count
    if detected_fillers == 0 and word_count > 0:
        for fw in FILLER_WORDS:
            detected_fillers += len(re.findall(r"\b" + re.escape(fw) + r"\b", lower_text))
    filler_evidence = f"{detected_fillers} filler words in {word_count} words"

    tradeoff_evidence = (
        f"trade-off terms: {len(matched_reasoning)} ({', '.join(matched_reasoning[:3])})"
        if matched_reasoning
        else "trade-off terms: 0"
    )

    tech_evidence = (
        f"{len(matched_tech)} domain keywords found ({', '.join(matched_tech[:4])})"
        if matched_tech
        else "0 domain keywords found"
    )

    missing_star = [k for k, v in star_hits.items() if not v]
    star_evidence = (
        f"{star_count}/4 STAR components identified"
        + (f" (missing: {', '.join(missing_star)})" if missing_star else "")
    )

    if resume_skills and len(resume_skills) > 0:
        resume_evidence = (
            f"{len(matched_resume)} of {len(resume_skills)} declared resume skills verified ({', '.join(matched_resume[:3]) if matched_resume else 'none'})"
        )
    else:
        resume_evidence = "No resume skills provided; evaluated against general engineering baseline"

    dimensions = {
        "structure": {
            "score": structure_score,
            "evidence": [
                f"{word_count} words across {sentence_count} sentence(s)",
                filler_evidence,
                f"{transitions} transition markers detected"
            ],
            "explanation": "Clear communicative structure with coherent narrative flow." if structure_score >= 70 else "Narrative flow is brief or lacks transitional signposting.",
            "recommended_action": "Structure responses into a clear 3-part narrative (Context, Action, Outcome) using explicit transitions ('First', 'Additionally', 'Finally')."
        },
        "technical": {
            "score": tech_score,
            "evidence": [
                tech_evidence,
                f"Evaluated category context: {category}"
            ],
            "explanation": f"Demonstrated solid domain concepts ({', '.join(matched_tech[:3]) if matched_tech else 'technical depth'})." if tech_score >= 70 else "Lacked specific architectural keywords or concrete protocol/database mechanisms.",
            "recommended_action": "Mention specific mechanisms (e.g., caching strategies, index types, concurrency models) rather than generic descriptions."
        },
        "reasoning": {
            "score": reasoning_score,
            "evidence": [
                tradeoff_evidence,
                "Causal rationale detected ('because', 'therefore')" if any(m in lower_text for m in ["because", "therefore", "as a result", "in order to"]) else "No causal justification markers found"
            ],
            "explanation": "Clearly articulated engineering tradeoffs and rationales." if reasoning_score >= 70 else "Focused primarily on 'what' was done rather than 'why' architectural choices were made.",
            "recommended_action": "Explicitly contrast your chosen architectural pattern against at least one viable alternative, noting the trade-offs."
        },
        "star": {
            "score": star_score,
            "evidence": [
                star_evidence,
                metric_evidence
            ],
            "explanation": "Followed the STAR method by highlighting action steps and tangible outcomes." if star_score >= 70 else "Incomplete STAR coverage; did not specify quantifiable final outcome.",
            "recommended_action": "Always close with the Result stage: quantify the business or performance outcome (e.g., % improvement, latency reduction, user count)."
        },
        "consistency": {
            "score": consistency_score,
            "evidence": [
                resume_evidence
            ],
            "explanation": "Skills and domain claims align with candidate's declared profile." if (resume_skills and len(matched_resume) > 0) else "General technical evaluation without resume verification linkage.",
            "recommended_action": "Anchor technical decisions with direct references to projects and technologies listed on your resume."
        }
    }

    # Construct Qualitative Feedback (Backward Compatible)
    strengths = []
    if structure_score >= 70:
        strengths.append("Clear communicative structure with coherent narrative flow.")
    if tech_score >= 70:
        strengths.append(f"Demonstrated solid domain concepts ({', '.join(matched_tech[:3]) if matched_tech else 'technical depth'}).")
    if reasoning_score >= 70:
        strengths.append("Clearly articulated engineering tradeoffs and rationales.")
    if star_score >= 70:
        strengths.append("Followed the STAR method by highlighting action steps and tangible outcomes.")
    if not strengths:
        strengths.append("Answer was direct and addressed the core question prompt.")

    weaknesses = []
    if word_count < WORD_COUNT_BANDS["minimal_detail"]:
        weaknesses.append("Response was too brief; missed opportunity to expand on operational details.")
    if tech_score < 60 and category.lower() == "technical":
        weaknesses.append("Lacked specific architectural keywords or concrete protocol/database mechanisms.")
    if not star_hits["result"] and category.lower() in ["behavioral", "hr"]:
        weaknesses.append("Did not specify the quantifiable final outcome or measurable impact.")
    if reasoning_score < 60:
        weaknesses.append("Focused primarily on 'what' was done rather than 'why' architectural choices were made.")
    if not weaknesses:
        weaknesses.append("Could provide more quantitative metrics or operational edge cases.")

    missing_concepts = []
    if category.lower() == "technical" and len(matched_tech) < 2:
        missing_concepts.extend(["Caching / Indexing tradeoffs", "Error handling & edge cases", "System scalability"])
    elif category.lower() in ["behavioral", "pressure"] and star_count < 3:
        missing_concepts.extend(["Concrete action steps taken by you", "Measurable project results", "Retrospective lessons learned"])
    else:
        missing_concepts.extend(["Performance benchmarking", "Long-term maintainability"])

    suggestions = [
        "Use the STAR model explicitly: briefly set the Situation, clarify your Task, detail your personal Actions, and end with the measurable Result.",
        "Include concrete metrics: e.g., 'reduced API response latency by 40%' or 'scaled to 10k daily active users'.",
        "Explain the 'why': contrast your choice against alternative designs to demonstrate senior engineering reasoning."
    ]

    return {
        "score": overall_score,
        "overall_score": overall_score,
        "structure_score": structure_score,
        "clarity_score": structure_score,
        "depth_score": tech_score,
        "technical_score": tech_score,
        "reasoning_score": reasoning_score,
        "star_score": star_score,
        "consistency_score": consistency_score,
        "dimensions": dimensions,
        "structure": dimensions["structure"],
        "technical": dimensions["technical"],
        "reasoning": dimensions["reasoning"],
        "star": dimensions["star"],
        "consistency": dimensions["consistency"],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_concepts": missing_concepts,
        "suggestions": suggestions
    }


def calculate_session_score(
    answer_scores: List[float],
    behavioral_score: float = 75.0,
    technical_scores: Optional[List[float]] = None,
    communication_scores: Optional[List[float]] = None,
    consistency_scores: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Weighted Session Score Formula:
    Final Readiness =
      0.30 * Communication
    + 0.30 * Technical
    + 0.20 * Behavioral
    + 0.20 * Resume Consistency
    """
    avg_answer = sum(answer_scores) / len(answer_scores) if answer_scores else 70.0

    comm_score = (
        round(sum(communication_scores) / len(communication_scores), 1)
        if communication_scores and len(communication_scores) > 0
        else round(avg_answer, 1)
    )

    tech_score = (
        round(sum(technical_scores) / len(technical_scores), 1)
        if technical_scores and len(technical_scores) > 0
        else round(avg_answer, 1)
    )

    beh_score = round(max(30.0, min(100.0, behavioral_score)), 1)

    cons_score = (
        round(sum(consistency_scores) / len(consistency_scores), 1)
        if consistency_scores and len(consistency_scores) > 0
        else 75.0
    )

    # Weighted formula using centralized weights
    w_comm = DEFAULT_SESSION_WEIGHTS["communication"]
    w_tech = DEFAULT_SESSION_WEIGHTS["technical"]
    w_deliv = DEFAULT_SESSION_WEIGHTS["delivery"]
    w_cons = DEFAULT_SESSION_WEIGHTS["resume_consistency"]

    final_readiness = round(
        w_comm * comm_score +
        w_tech * tech_score +
        w_deliv * beh_score +
        w_cons * cons_score,
        1
    )

    subscores = {
        "Communication": comm_score,
        "Technical": tech_score,
        "Behavioral": beh_score,
        "Resume Consistency": cons_score
    }

    strongest = max(subscores.items(), key=lambda x: x[1])[0]
    weakest = min(subscores.items(), key=lambda x: x[1])[0]

    insights = [
        f"Strongest area is {strongest} with an average score of {subscores[strongest]}%.",
        f"Primary growth opportunity lies in {weakest} (currently at {subscores[weakest]}%).",
        "Adopt the STAR method consistently and quantify project results with percentages and engineering metrics."
    ]

    return {
        "final_readiness_score": final_readiness,
        "communication_score": comm_score,
        "technical_score": tech_score,
        "behavioral_score": beh_score,
        "resume_consistency_score": cons_score,
        "strongest_category": strongest,
        "weakest_category": weakest,
        "insights": insights
    }
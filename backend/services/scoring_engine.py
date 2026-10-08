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

    TRIVIAL_NON_ANSWERS = {
        "idk", "i don't know", "idk.", "no", "yes", "skip", "none", "pass", "na", "n/a",
        "dsjnd", "test", "asdf", "hello", "hi", "bye", "ok", "okay"
    }

    if word_count == 0:
        empty_dimensions = {
            "structure": {
                "score": 0.0,
                "evidence": ["0 words submitted (empty answer)"],
                "explanation": "No response text was submitted.",
                "recommended_action": "Provide a complete verbal or written technical explanation."
            },
            "technical": {
                "score": 0.0,
                "evidence": ["0 domain keywords found"],
                "explanation": "No technical concepts or mechanisms were provided.",
                "recommended_action": "Describe specific tools, frameworks, protocols, and architectural patterns."
            },
            "reasoning": {
                "score": 0.0,
                "evidence": ["No trade-offs or rationale provided"],
                "explanation": "No reasoning or comparative evaluation detected.",
                "recommended_action": "Articulate why an engineering decision was made and compare against alternatives."
            },
            "star": {
                "score": 0.0,
                "evidence": ["0 STAR components identified"],
                "explanation": "No STAR elements detected in empty response.",
                "recommended_action": "Use the STAR method: Situation, Task, Action, and Result."
            },
            "consistency": {
                "score": 0.0,
                "evidence": ["No evidence to compare against resume"],
                "explanation": "Could not verify background claims from an empty answer.",
                "recommended_action": "Reference specific project experiences from your background."
            }
        }
        return {
            "score": 0.0,
            "overall_score": 0.0,
            "structure_score": 0.0,
            "clarity_score": 0.0,
            "depth_score": 0.0,
            "technical_score": 0.0,
            "reasoning_score": 0.0,
            "star_score": 0.0,
            "consistency_score": 0.0,
            "answer_status": "EMPTY",
            "dimensions": empty_dimensions,
            "structure": empty_dimensions["structure"],
            "technical": empty_dimensions["technical"],
            "reasoning": empty_dimensions["reasoning"],
            "star": empty_dimensions["star"],
            "consistency": empty_dimensions["consistency"],
            "strengths": [],
            "weaknesses": ["Empty answer submitted; no evidence collected."],
            "missing_concepts": ["Complete technical explanation", "Architectural mechanisms", "Trade-offs"],
            "suggestions": ["Provide a detailed verbal or written answer addressing the question directly."]
        }

    if word_count < 4 or lower_text in TRIVIAL_NON_ANSWERS:
        insufficient_dims = {
            "structure": {
                "score": 0.0,
                "evidence": [f"{word_count} words submitted", "Insufficient narrative structure"],
                "explanation": "Answer is too brief or trivial to assess narrative flow.",
                "recommended_action": "Provide a complete verbal or written response of at least 40 words."
            },
            "technical": {
                "score": 0.0,
                "evidence": ["0 domain keywords found", f"Evaluated category: {category}"],
                "explanation": "No technical concepts or mechanisms were provided.",
                "recommended_action": "Describe specific tools, frameworks, protocols, and architectural patterns."
            },
            "reasoning": {
                "score": 0.0,
                "evidence": ["No comparative justification or trade-offs found"],
                "explanation": "No rationale or comparative trade-offs were detected.",
                "recommended_action": "Articulate why an engineering decision was made and compare against alternatives."
            },
            "star": {
                "score": 0.0,
                "evidence": ["0/4 STAR components identified"],
                "explanation": "No STAR elements detected in response.",
                "recommended_action": "Use the STAR method: Situation, Task, Action, and measurable Result."
            },
            "consistency": {
                "score": 0.0,
                "evidence": ["Insufficient text to cross-reference against resume skills"],
                "explanation": "Could not verify background claims from an insufficient or single-token answer.",
                "recommended_action": "Reference specific project experiences from your background."
            }
        }
        return {
            "score": 0.0,
            "overall_score": 0.0,
            "structure_score": 0.0,
            "clarity_score": 0.0,
            "depth_score": 0.0,
            "technical_score": 0.0,
            "reasoning_score": 0.0,
            "star_score": 0.0,
            "consistency_score": 0.0,
            "answer_status": "INSUFFICIENT",
            "dimensions": insufficient_dims,
            "structure": insufficient_dims["structure"],
            "technical": insufficient_dims["technical"],
            "reasoning": insufficient_dims["reasoning"],
            "star": insufficient_dims["star"],
            "consistency": insufficient_dims["consistency"],
            "strengths": [],
            "weaknesses": ["Answer is insufficient or trivial; does not address the question."],
            "missing_concepts": ["Direct answer to the question", "Technical mechanisms", "Implementation details"],
            "suggestions": ["Elaborate on your answer with concrete technical mechanisms, trade-offs, and examples."]
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

    # Construct Contextual, Human-Interviewer Qualitative Feedback (No Generic Robotic Templates)
    tech_str = ", ".join(matched_tech[:3]) if matched_tech else None

    strengths = []
    if tech_score >= 70 and tech_str:
        strengths.append(f"You grounded your technical explanation in concrete tools and mechanisms ({tech_str}).")
    elif structure_score >= 70:
        strengths.append("Your response had a coherent progression from context into your specific implementation.")

    if reasoning_score >= 70 and matched_reasoning:
        strengths.append(f"You articulated the architectural rationale behind your choices ({', '.join(matched_reasoning[:2])}).")

    if not strengths:
        if tech_str:
            strengths.append(f"You referenced relevant engineering technologies ({tech_str}) directly addressing the question topic.")
        else:
            strengths.append("You directly engaged with the interview prompt without evading the question.")

    weaknesses = []
    what_was_missing = []

    # Format: WHAT HAPPENED, WHY IT MATTERS, WHAT TO DO NEXT
    if word_count < WORD_COUNT_BANDS["minimal_detail"]:
        gap = (
            "What happened: Your answer was brief and stopped at high-level statements.\n"
            "Why it matters: In a technical interview, an interviewer expects you to unpack the implementation details and challenges, not just summarize the final state.\n"
            "What to do next: Walk through the request lifecycle or component flow step-by-step, explaining how data travels through the system."
        )
        weaknesses.append("Your response stayed fairly general. Give one concrete example from the project instead of describing it broadly.")
        what_was_missing.append(gap)

    if tech_score < 60 and category.lower() == "technical":
        if tech_str:
            gap = (
                f"What happened: You mentioned {tech_str}, but did not explain how you configured it, structured data, or resolved concurrency.\n"
                "Why it matters: Simply naming tools confirms familiarity, but interviewers look for defensible architectural decisions and trade-offs.\n"
                "What to do next: Explain why you chose this tool over alternatives and detail one concrete operational challenge you resolved."
            )
            weaknesses.append(f"You mentioned {tech_str}, but did not explain why you chose it over alternatives or how you handled operational edge cases.")
        else:
            gap = (
                "What happened: You described the concept conceptually without mentioning specific protocols, database engines, or frameworks.\n"
                "Why it matters: Senior interviewers look for verified hands-on engineering experience rather than purely theoretical definitions.\n"
                "What to do next: Anchor your answer in a specific technology stack (e.g., PostgreSQL indexing, Redis caching, or FastAPI middleware)."
            )
            weaknesses.append("Your explanation was mostly conceptual. Anchor your answer with specific protocols, database engines, or frameworks.")
        what_was_missing.append(gap)

    if reasoning_score < 60:
        gap = (
            "What happened: You focused on what was built rather than why that architectural pattern was selected over alternatives.\n"
            "Why it matters: Engineering maturity is judged by how well you understand the trade-offs (latency vs. complexity, consistency vs. availability) of your choices.\n"
            "What to do next: Explicitly contrast your design against at least one viable alternative and explain what constraint drove your decision."
        )
        weaknesses.append("You described what was done, but did not explain the trade-offs or why you chose this design over alternatives.")
        what_was_missing.append(gap)

    if not weaknesses:
        weaknesses.append("Your explanation was solid, but adding one concrete production metric or failure edge case would make it even stronger.")
        what_was_missing.append(
            "What happened: The solution covered the primary path well, but skipped production telemetry.\n"
            "Why it matters: Production readiness requires understanding failure modes and observability.\n"
            "What to do next: Mention specific error handling strategies or monitoring metrics (e.g. latency percentiles, database query times)."
        )

    # Human-readable suggestions
    suggestions = []
    if tech_str:
        suggestions.append(f"In your next answer, explain how {tech_str} interacted with other tiers under concurrent load.")
    else:
        suggestions.append("Name the exact libraries, databases, or cloud services you used rather than using passive descriptions like 'the backend'.")

    missing_concepts = []
    if category.lower() == "technical" and len(matched_tech) < 2:
        missing_concepts.extend(["Caching / Indexing tradeoffs", "Error handling & edge cases", "System scalability"])
    elif category.lower() in ["behavioral", "pressure"] and star_count < 3:
        missing_concepts.extend(["Concrete action steps taken by you", "Measurable project results", "Retrospective lessons learned"])
    else:
        missing_concepts.extend(["Performance benchmarking", "Long-term maintainability"])

    overall_assessment = (
        f"You demonstrated a good practical grasp of {tech_str or 'the topic'}, but the interviewer would probe deeper into operational trade-offs and edge cases."
        if overall_score >= 65 else
        f"You introduced the right direction with {tech_str or 'your concepts'}, but the explanation needs more depth on architecture, data flow, and why decisions were made."
    )

    # 6. Directness & Evasion Detection
    q_lower = (question_text or "").lower()
    asking_measurement = any(k in q_lower for k in ["measure", "baseline", "metric", "how did you verify", "benchmark", "quantify"])
    asking_tradeoff = any(k in q_lower for k in ["tradeoff", "trade-off", "alternative", "why did you choose", "instead of"])
    has_numbers = bool(re.search(r"\b\d+(\.\d+)?%?|\b\d+(?:ms|s|m|k|mb|gb|rps|qps)\b", lower_text))
    has_tradeoff_words = any(k in lower_text for k in ["because", "instead of", "tradeoff", "trade-off", "rather than", "alternative", "compared to"])

    candidate_diversion = False
    unresolved_point = None
    directness_score = 85.0

    if asking_measurement and not has_numbers:
        candidate_diversion = True
        directness_score = 35.0
        unresolved_point = f"Specific baseline measurement and quantitative evidence for: '{question_text[:60]}'"
    elif asking_tradeoff and not has_tradeoff_words:
        candidate_diversion = True
        directness_score = 45.0
        unresolved_point = f"Architectural tradeoff justification for: '{question_text[:60]}'"
    elif word_count < WORD_COUNT_BANDS["minimal_detail"]:
        directness_score = 40.0
        unresolved_point = f"Elaboration and technical depth on: '{question_text[:60]}'"

    if candidate_diversion:
        weaknesses.append("Response diverged or lacked direct evidence for the specific mechanism asked.")

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
        "directness_score": directness_score,
        "candidate_diversion": candidate_diversion,
        "unresolved_point": unresolved_point,
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
        "missing_concepts": missing_concepts,
        "suggestions": suggestions
    }


def calculate_session_score(
    answer_scores: List[float],
    delivery_score: Optional[float] = None,
    technical_scores: Optional[List[float]] = None,
    communication_scores: Optional[List[float]] = None,
    consistency_scores: Optional[List[float]] = None,
    behavioral_score: Optional[float] = None,
    evidence_coverage: Optional[float] = None
) -> Dict[str, Any]:
    """
    Weighted Session Score Formula.
    EVIDENCE-GATED: If no answer scores are submitted (zero answers or all skipped),
    readiness score MUST be 0.0 with Low assessment confidence and Incomplete status.

    When Delivery & Visual Stability is measured:
      Final Readiness = 0.30 Communication + 0.30 Technical + 0.20 Delivery + 0.20 Resume Consistency

    When Delivery is unmeasured (camera off or denied):
      Delivery is excluded completely, and remaining weights are re-normalized proportionally:
      Communication: 0.30 / 0.80 = 0.375
      Technical:     0.30 / 0.80 = 0.375
      Resume:        0.20 / 0.80 = 0.250
      Final Readiness = 0.375 Communication + 0.375 Technical + 0.250 Resume Consistency
    """
    if not answer_scores:
        return {
            "final_readiness_score": 0.0,
            "communication_score": 0.0,
            "technical_score": 0.0,
            "delivery_score": None,
            "delivery_measured": False,
            "behavioral_score": None,
            "resume_consistency_score": 0.0,
            "score_confidence": "Low",
            "confidence_explanation": "No meaningful interview answers were submitted, so readiness cannot be reliably assessed.",
            "weights_used": {
                "communication": 0.375,
                "technical": 0.375,
                "delivery": 0.0,
                "resume_consistency": 0.25
            },
            "strongest_category": "None (Insufficient Evidence)",
            "weakest_category": "All Dimensions (Evidence Missing)",
            "insights": [
                "Interview incomplete: no meaningful answers were submitted to evaluate readiness.",
                "Complete interview questions to generate verified technical and communication scores."
            ]
        }

    avg_answer = sum(answer_scores) / len(answer_scores)

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

    cons_score = (
        round(sum(consistency_scores) / len(consistency_scores), 1)
        if consistency_scores and len(consistency_scores) > 0
        else round(avg_answer, 1)
    )

    # Determine delivery score (support both delivery_score and legacy behavioral_score)
    actual_delivery = delivery_score if delivery_score is not None else behavioral_score

    if actual_delivery is not None:
        deliv_score = round(max(0.0, min(100.0, actual_delivery)), 1)
        delivery_measured = True
        weights_used = {
            "communication": DEFAULT_SESSION_WEIGHTS["communication"],
            "technical": DEFAULT_SESSION_WEIGHTS["technical"],
            "delivery": DEFAULT_SESSION_WEIGHTS["delivery"],
            "resume_consistency": DEFAULT_SESSION_WEIGHTS["resume_consistency"],
        }
        final_readiness = round(
            weights_used["communication"] * comm_score +
            weights_used["technical"] * tech_score +
            weights_used["delivery"] * deliv_score +
            weights_used["resume_consistency"] * cons_score,
            1
        )
        subscores = {
            "Communication": comm_score,
            "Technical": tech_score,
            "Delivery & Visual Stability": deliv_score,
            "Resume Consistency": cons_score
        }
    else:
        deliv_score = None
        delivery_measured = False
        # Proportional re-normalization: total remaining weight is 0.80
        total_remaining = (
            DEFAULT_SESSION_WEIGHTS["communication"] +
            DEFAULT_SESSION_WEIGHTS["technical"] +
            DEFAULT_SESSION_WEIGHTS["resume_consistency"]
        )
        weights_used = {
            "communication": round(DEFAULT_SESSION_WEIGHTS["communication"] / total_remaining, 3),  # 0.375
            "technical": round(DEFAULT_SESSION_WEIGHTS["technical"] / total_remaining, 3),          # 0.375
            "delivery": 0.0,
            "resume_consistency": round(DEFAULT_SESSION_WEIGHTS["resume_consistency"] / total_remaining, 3), # 0.25
        }
        final_readiness = round(
            weights_used["communication"] * comm_score +
            weights_used["technical"] * tech_score +
            weights_used["resume_consistency"] * cons_score,
            1
        )
        subscores = {
            "Communication": comm_score,
            "Technical": tech_score,
            "Resume Consistency": cons_score
        }

    strongest = max(subscores.items(), key=lambda x: x[1])[0]
    weakest = min(subscores.items(), key=lambda x: x[1])[0]

    insights = [
        f"Strongest area is {strongest} with an average score of {subscores[strongest]}%.",
        f"Primary growth opportunity lies in {weakest} (currently at {subscores[weakest]}%).",
    ]
    if delivery_measured:
        insights.append("Adopt the STAR method consistently and quantify project results with percentages and engineering metrics.")
    else:
        insights.append("Note: Delivery & Visual Stability was not measured (camera was off/denied). Readiness was re-normalized across Communication (37.5%), Technical (37.5%), and Resume Consistency (25.0%).")

    num_answers = len(answer_scores)
    if evidence_coverage is not None and evidence_coverage < 50.0:
        score_confidence = "Low"
        confidence_explanation = f"Low confidence ({round(evidence_coverage, 1)}% evidence coverage). Complete more questions for full readiness assessment."
    elif num_answers >= 5:
        score_confidence = "High"
        confidence_explanation = f"High assessment confidence based on {num_answers} evaluated turns."
    elif num_answers >= 3:
        score_confidence = "Moderate"
        confidence_explanation = f"Moderate assessment confidence based on {num_answers} evaluated turns."
    else:
        score_confidence = "Low"
        confidence_explanation = f"Initial score estimate based on {num_answers} turn(s). Complete more questions for maximum accuracy."

    return {
        "final_readiness_score": final_readiness,
        "communication_score": comm_score,
        "technical_score": tech_score,
        "delivery_score": deliv_score,
        "delivery_measured": delivery_measured,
        "behavioral_score": deliv_score,  # backward compatibility alias
        "resume_consistency_score": cons_score,
        "score_confidence": score_confidence,
        "confidence_explanation": confidence_explanation,
        "weights_used": weights_used,
        "strongest_category": strongest,
        "weakest_category": weakest,
        "insights": insights
    }
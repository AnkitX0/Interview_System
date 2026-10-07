"""
backend/services/evidence_sufficiency_engine.py
Evidence Sufficiency Engine & Dynamic State Machine for Adaptive Interviews.
Determines whether an interview should continue based on evidence sufficiency,
unresolved claims, evasion flags, and policy constraints rather than rigid question limits.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from backend.config import INTERVIEW_POLICY_CONFIG, MAX_ADAPTIVE_SAFETY_CEILING, INTERVIEW_STATES


@dataclass
class SufficiencyResult:
    continue_interview: bool
    reason: str
    priority_next_topic: str
    evidence_gaps: List[str] = field(default_factory=list)
    recommended_depth: int = 2
    confidence: str = "Moderate"
    interview_state: str = "EXPLORING"


def resolve_session_policy(
    policy_key: Optional[str],
    total_questions: Optional[int] = None,
    question_mode: Optional[str] = "ADAPTIVE",
) -> Dict[str, Any]:
    """
    Resolves policy dictionary from string key or maps integer budget (5, 8, 12, etc.)
    for 100% backward compatibility and test stability.
    """
    key_upper = (policy_key or "").upper()
    if key_upper in INTERVIEW_POLICY_CONFIG:
        base = dict(INTERVIEW_POLICY_CONFIG[key_upper])
        if (question_mode or "").upper() == "FIXED" and total_questions:
            base["maximum_questions"] = total_questions
            base["minimum_questions"] = total_questions
        return base

    if total_questions is not None:
        if (question_mode or "").upper() == "FIXED" or total_questions <= 3:
            return {
                "mode": "DRILL",
                "minimum_questions": total_questions,
                "maximum_questions": total_questions,
                "minimum_evidence_dimensions": 2,
                "minimum_topics": 1,
                "minimum_resume_claims": 1,
                "minimum_followups": 1,
                "label": f"Targeted Scope ({total_questions} questions)",
            }
        elif total_questions <= 5:
            return dict(INTERVIEW_POLICY_CONFIG["SHORT"])
        elif total_questions <= 9:
            return dict(INTERVIEW_POLICY_CONFIG["STANDARD"])
        elif total_questions <= 15:
            return dict(INTERVIEW_POLICY_CONFIG["DEEP"])
        else:
            return dict(INTERVIEW_POLICY_CONFIG["FULL"])

    return dict(INTERVIEW_POLICY_CONFIG["STANDARD"])


def assess_interview_sufficiency(
    questions_completed: int,
    answers_evaluated: int,
    topics_covered: List[str],
    resume_claims_examined: int,
    weak_topics: List[str],
    strong_topics: List[str],
    unresolved_points: List[Any],
    evasion_count: int,
    follow_up_count: int,
    technical_evidence: Optional[Dict[str, Any]] = None,
    behavioral_evidence: Optional[Dict[str, Any]] = None,
    problem_solving_evidence: Optional[Dict[str, Any]] = None,
    communication_evidence: Optional[Dict[str, Any]] = None,
    delivery_data: Optional[Dict[str, Any]] = None,
    confidence_in_assessment: Optional[str] = None,
    policy_key: Optional[str] = "STANDARD",
    nominal_total_questions: Optional[int] = None,
    question_mode: Optional[str] = "ADAPTIVE",
) -> SufficiencyResult:
    """
    Evaluates multi-dimensional evidence to determine if the interviewer should ask another question.
    """
    policy = resolve_session_policy(policy_key, nominal_total_questions, question_mode)
    min_q = policy.get("minimum_questions", 5)
    max_q = policy.get("maximum_questions", 12)
    min_topics = policy.get("minimum_topics", 3)
    min_claims = policy.get("minimum_resume_claims", 2)

    # 1. Hard Safety Ceiling to prevent runaway API loops or exhaustion
    if questions_completed >= MAX_ADAPTIVE_SAFETY_CEILING:
        return SufficiencyResult(
            continue_interview=False,
            reason="Maximum interview depth reached. We have enough evidence to generate your assessment.",
            priority_next_topic="final_synthesis",
            evidence_gaps=[],
            recommended_depth=4,
            confidence="High",
            interview_state="FINAL_ASSESSMENT",
        )

    # 2. Strict minimum question budget not yet reached
    if questions_completed < min_q:
        if questions_completed <= 1:
            state = "STARTING"
            depth = 1
        elif questions_completed <= 3:
            state = "EXPLORING"
            depth = 2
        else:
            state = "DEEP_DIVING"
            depth = 3

        gaps = []
        if len(topics_covered) < min_topics:
            gaps.append("additional_domain_topics")
        if resume_claims_examined < min_claims:
            gaps.append("resume_claim_grounding")

        return SufficiencyResult(
            continue_interview=True,
            reason=f"Candidate assessment in progress ({questions_completed}/{min_q} minimum turns completed). Collecting foundational evidence.",
            priority_next_topic=topics_covered[-1] if topics_covered else "system_architecture",
            evidence_gaps=gaps or ["technical_depth"],
            recommended_depth=depth,
            confidence="Low" if questions_completed < 3 else "Moderate",
            interview_state=state,
        )

    # 3. Between Minimum and Maximum Questions
    # Check if there are active evasions or unresolved claims
    if unresolved_points:
        unresolved_item = unresolved_points[-1]
        point_text = unresolved_item.get("unresolved_point", "claimed metric") if isinstance(unresolved_item, dict) else str(unresolved_item)
        return SufficiencyResult(
            continue_interview=True,
            reason=f"Important claim/explanation remains unresolved: {point_text}.",
            priority_next_topic="unresolved_claim_defense",
            evidence_gaps=["measurement_methodology", "baseline_evidence"],
            recommended_depth=4,
            confidence="Moderate",
            interview_state="VERIFYING",
        )

    # Check if resume claims have been sufficiently sampled
    if resume_claims_examined < min_claims:
        return SufficiencyResult(
            continue_interview=True,
            reason="Resume claims remain insufficiently verified; probing candidate project achievements.",
            priority_next_topic="project_architecture",
            evidence_gaps=["architecture_decisions", "tradeoffs"],
            recommended_depth=3,
            confidence="Moderate",
            interview_state="DEEP_DIVING",
        )

    # Check if strong answers justify deeper challenge (Level 4-7)
    if strong_topics and questions_completed < max_q and follow_up_count < 2:
        return SufficiencyResult(
            continue_interview=True,
            reason=f"Candidate demonstrated high competence in {strong_topics[-1]}; escalating to edge case and failure recovery.",
            priority_next_topic=strong_topics[-1],
            evidence_gaps=["extreme_concurrency", "incident_recovery"],
            recommended_depth=5,
            confidence="Moderate",
            interview_state="CHALLENGING",
        )

    # Check topic coverage diversity
    if len(topics_covered) < min_topics and questions_completed < max_q:
        return SufficiencyResult(
            continue_interview=True,
            reason=f"Only {len(topics_covered)} of {min_topics} required domain topics covered; broadening interview scope.",
            priority_next_topic="system_design",
            evidence_gaps=["breadth_of_role_knowledge"],
            recommended_depth=2,
            confidence="Moderate",
            interview_state="BALANCING",
        )

    # 4. Sufficient evidence collected or reached max question limit
    if questions_completed >= max_q:
        return SufficiencyResult(
            continue_interview=False,
            reason=f"Target session scope reached ({max_q} questions). Calibrated evidence collected across all dimensions.",
            priority_next_topic="final_assessment",
            evidence_gaps=[],
            recommended_depth=4,
            confidence="High",
            interview_state="FINAL_ASSESSMENT",
        )

    # All criteria satisfied before max_q!
    return SufficiencyResult(
        continue_interview=False,
        reason="Enough evidence collected across technical depth, communication, and resume defense to formulate calibrated assessment.",
        priority_next_topic="final_assessment",
        evidence_gaps=[],
        recommended_depth=3,
        confidence="High" if questions_completed >= 7 else "Moderate",
        interview_state="FINAL_ASSESSMENT",
    )

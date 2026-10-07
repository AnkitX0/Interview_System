"""
backend/services/adaptive_engine.py
Memory-Based Interview Intelligence Engine v2.
Integrates InterviewMemory, Evasion Return Probing, Depth Escalation,
and Deterministic & LLM Question Decisions.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import re

from sqlalchemy.orm import Session
import backend.models as models
from backend.services.question_selector import select_questions
from backend.config import PRESSURE_MODE_CONFIG
from backend.services.probe_rephraser import rephrase_probe_question
from backend.services.interview_memory_service import build_interview_memory, InterviewMemory
from backend.services.llm_question_provider import generate_llm_adaptive_question
from backend.services.evidence_sufficiency_engine import assess_interview_sufficiency, resolve_session_policy
from backend.services.llm_gemini_service import decide_llm_question_strategy


LADDER_STAGES = [
    "T1_FOUNDATION",
    "T2_TRADE_OFFS",
    "T3_INCIDENT",
    "T4_EDGE_CASE",
]

PROBE_TEMPLATES: Dict[str, List[str]] = {
    "T1_FOUNDATION": [
        "In your resume, you highlighted: '{claim}'. Walk me through your specific role, the system architecture, and how the core mechanism was implemented.",
        "Regarding your project claim '{claim}': what was the underlying architecture and how did the components communicate end-to-end?",
        "You stated that you '{claim}'. What specific technologies, data models, or APIs did you build to achieve this?",
    ],
    "T2_TRADE_OFFS": [
        "Building on your work with '{claim}': what alternative architectural patterns or technologies did you evaluate, and what were the main tradeoffs?",
        "For '{claim}': what were the performance or complexity tradeoffs of your approach, and why did you choose this over simpler designs?",
        "When implementing '{claim}', what technical compromises did you have to accept, and how did you justify them?",
    ],
    "T3_INCIDENT": [
        "Thinking back to '{claim}': describe a memorable production failure, bottleneck, or bug that occurred, and how you diagnosed and resolved it.",
        "During the deployment or operation of '{claim}', what unexpected edge behavior or outage occurred, and what was your debugging process?",
        "Walk me through a high-severity incident or performance degradation you encountered while maintaining '{claim}'.",
    ],
    "T4_EDGE_CASE": [
        "If the workload or traffic for '{claim}' scaled by 10x or 100x overnight, what component would fail first, and how would you re-architect it?",
        "Consider race conditions, network partitions, or data corruption in '{claim}': how does your design guard against these edge scenarios?",
        "Under extreme concurrency or resource exhaustion, how does '{claim}' degrade gracefully or handle backpressure?",
    ],
}


@dataclass
class PolicyDecisionResult:
    decision: str
    reason: str
    inputs: Dict[str, Any]
    question_type: str = "bank"
    source: str = "bank"
    claim_id: Optional[int] = None
    ladder_stage: Optional[str] = None
    difficulty: str = "medium"
    time_limit_seconds: Optional[int] = None
    question_text: str = ""


def _deterministic_template_choice(templates: List[str], seed_str: str) -> str:
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
    return templates[h % len(templates)]


def format_probe_question(claim_text: str, stage: str) -> str:
    clean_claim = claim_text.strip()
    if clean_claim.endswith("."):
        clean_claim = clean_claim[:-1]
    templates = PROBE_TEMPLATES.get(stage, PROBE_TEMPLATES["T1_FOUNDATION"])
    tmpl = _deterministic_template_choice(templates, f"{stage}:{clean_claim}")
    return tmpl.format(claim=clean_claim)


def calculate_adjusted_difficulty(evaluations: List[models.AnswerEvaluation], current_difficulty: str) -> str:
    if not evaluations:
        return current_difficulty

    recent_scores = [ev.overall_score for ev in evaluations[-3:] if ev.overall_score is not None]
    if not recent_scores:
        return current_difficulty

    avg_score = sum(recent_scores) / len(recent_scores)
    diff_order = ["easy", "medium", "hard"]
    curr_idx = diff_order.index(current_difficulty.lower()) if current_difficulty.lower() in diff_order else 1

    if avg_score >= 80.0 and curr_idx < 2:
        return diff_order[curr_idx + 1]
    elif avg_score < 60.0 and curr_idx > 0:
        return diff_order[curr_idx - 1]

    return current_difficulty


def decide_next_question(
    session: models.InterviewSession,
    answers: List[models.InterviewAnswer],
    evaluations: List[models.AnswerEvaluation],
    claims: List[models.ResumeClaim],
    questions_asked: List[models.InterviewQuestion],
    db: Session,
) -> PolicyDecisionResult:
    """
    Memory-Based Interview Intelligence Policy Engine v2.
    Decides the next question considering InterviewMemory, evasion detection,
    depth escalation, resume claim verification, and repetition prevention.
    """
    turn = len(questions_asked) + 1
    total_answers = len(answers)

    # Build InterviewMemory model
    memory = build_interview_memory(session.id, db)

    # 1. Evaluate Evidence Sufficiency Engine (Unlimited Adaptive Policy)
    policy_key = getattr(session, "session_policy", None) or "STANDARD"
    q_mode = getattr(session, "question_mode", None) or "ADAPTIVE"

    sufficiency = assess_interview_sufficiency(
        questions_completed=total_answers,
        answers_evaluated=len(evaluations),
        topics_covered=memory.topics_covered,
        resume_claims_examined=len({q.claim_id for q in questions_asked if q.claim_id is not None}),
        weak_topics=memory.weak_areas,
        strong_topics=memory.strong_areas,
        unresolved_points=memory.unresolved_points,
        evasion_count=len(memory.evasion_history),
        follow_up_count=sum(1 for q in questions_asked if q.question_type == "probe"),
        policy_key=policy_key,
        nominal_total_questions=session.total_questions,
        question_mode=q_mode,
    )

    if hasattr(session, "interview_state"):
        session.interview_state = sufficiency.interview_state

    # Complete session only when evidence is sufficient or hard safety limit reached
    if not sufficiency.continue_interview:
        return PolicyDecisionResult(
            decision="COMPLETE_SESSION",
            reason=sufficiency.reason,
            inputs={
                "total_questions": session.total_questions,
                "answers_count": total_answers,
                "interview_state": sufficiency.interview_state,
                "confidence": sufficiency.confidence,
            },
        )

    adjusted_difficulty = calculate_adjusted_difficulty(evaluations, session.difficulty or "medium")
    asked_texts = {q.question_text for q in questions_asked}

    # 1.5 CHECK 0: Pressure Mode Challenge Triggering
    if session.mode == "pressure" and answers:
        challenges_asked = [q for q in questions_asked if q.question_type == "challenge"]
        max_challenges = PRESSURE_MODE_CONFIG.get("max_challenges_per_session", 2)
        last_q_is_challenge = bool(questions_asked and questions_asked[-1].question_type == "challenge")

        if len(challenges_asked) < max_challenges and not last_q_is_challenge:
            last_text = (answers[-1].transcript or "").lower()
            templates = PRESSURE_MODE_CONFIG.get("challenge_templates", {})

            # Check numeric metrics pattern
            num_pattern = re.compile(r'\d+%\b|\b\d+\s*(ms|s|rps|tps|mb|gb|tb|req|users|queries)\b|\b\d+\s*percent\b', re.IGNORECASE)
            if num_pattern.search(last_text):
                num_templates = templates.get("numeric_validation", ["You cited a specific quantitative metric. How did you benchmark or validate that number in production?"])
                q_text = _deterministic_template_choice(num_templates, f"numeric:{session.id}:{len(questions_asked)}")
                if q_text not in asked_texts:
                    return PolicyDecisionResult(
                        decision="TRIGGER_CHALLENGE",
                        reason="Quantitative metric detected in response during Pressure Mode; triggering numeric validation challenge.",
                        inputs={"challenge_category": "numeric_validation"},
                        question_type="challenge",
                        source="pressure",
                        difficulty=adjusted_difficulty,
                        time_limit_seconds=45,
                        question_text=q_text,
                    )

            # Check architectural patterns
            arch_pattern = re.compile(r'\b(microservices|kafka|rabbitmq|postgresql|postgres|redis|cassandra|mongodb|architecture|design|asynchronous|event-driven|distributed|grpc|load balancer)\b', re.IGNORECASE)
            if arch_pattern.search(last_text):
                arch_templates = templates.get("counterexample_failure", ["What would occur if that architectural approach encountered extreme concurrency or sudden resource exhaustion in production?"])
                q_text = _deterministic_template_choice(arch_templates, f"arch:{session.id}:{len(questions_asked)}")
                if q_text not in asked_texts:
                    return PolicyDecisionResult(
                        decision="TRIGGER_CHALLENGE",
                        reason="Architectural design choice detected in response during Pressure Mode; triggering counterexample challenge.",
                        inputs={"challenge_category": "counterexample_failure"},
                        question_type="challenge",
                        source="pressure",
                        difficulty=adjusted_difficulty,
                        time_limit_seconds=45,
                        question_text=q_text,
                    )

    # 2. CHECK 1: Evasion Return Probing (Return to unresolved point if candidate evaded)
    if memory.unresolved_points:
        unresolved = memory.unresolved_points[-1]
        evasion_q = (
            f"Regarding your response to '{unresolved['question_text'][:50]}...': "
            f"You mentioned general context, but I want to focus on {unresolved['unresolved_point']}. "
            f"How did you establish the baseline and what specific metrics supported your decision?"
        )
        if evasion_q not in asked_texts:
            return PolicyDecisionResult(
                decision="RETURN_TO_UNRESOLVED_POINT",
                reason=f"Candidate evaded core question in Turn {unresolved['turn']}; returning to unresolved point.",
                inputs={"unresolved_turn": unresolved["turn"], "unresolved_point": unresolved["unresolved_point"]},
                question_type="probe",
                source="interview_memory",
                difficulty=adjusted_difficulty,
                time_limit_seconds=45 if session.mode == "pressure" else 90,
                question_text=evasion_q,
            )

    # 3. CHECK 2: Advance Claim Probe Ladder (Priority 2: Resume Claim Defense)
    last_q = questions_asked[-1] if questions_asked else None
    if last_q and last_q.claim_id is not None and last_q.ladder_stage:
        claim_probes = [q for q in questions_asked if q.claim_id == last_q.claim_id]
        last_eval = evaluations[-1] if evaluations else None
        last_score = last_eval.overall_score if last_eval else 70.0

        target_claim = next((c for c in claims if c.id == last_q.claim_id), None)

        if len(claim_probes) < 3 and last_score >= 65.0 and target_claim:
            curr_stage_idx = LADDER_STAGES.index(last_q.ladder_stage) if last_q.ladder_stage in LADDER_STAGES else 0
            if curr_stage_idx < len(LADDER_STAGES) - 1:
                next_stage = LADDER_STAGES[curr_stage_idx + 1]
                tmpl_q = format_probe_question(target_claim.claim_text, next_stage)
                q_text = rephrase_probe_question(target_claim.claim_text, next_stage, tmpl_q)
                if q_text not in asked_texts:
                    return PolicyDecisionResult(
                        decision="ADVANCE_LADDER",
                        reason=f"Candidate handled {last_q.ladder_stage} (score {last_score:.1f}); advancing to {next_stage}.",
                        inputs={
                            "claim_id": target_claim.id,
                            "previous_stage": last_q.ladder_stage,
                            "next_stage": next_stage,
                            "last_score": last_score,
                        },
                        question_type="probe",
                        source="resume_claim",
                        claim_id=target_claim.id,
                        ladder_stage=next_stage,
                        difficulty=adjusted_difficulty,
                        time_limit_seconds=45 if session.mode == "pressure" else 90,
                        question_text=q_text,
                    )

    # 4. CHECK 3: Probe Weak Answer Depth (If last technical score < 60)
    if evaluations:
        last_eval = evaluations[-1]
        last_q = questions_asked[-1] if questions_asked else None
        if last_eval and last_eval.technical_score < 60.0 and last_q:
            weak_q = (
                f"Your previous response on '{last_q.question_text[:40]}...' stayed high-level. "
                f"Walk me through the exact underlying protocol or architectural mechanism you used, "
                f"and what specific parameters you configured."
            )
            if weak_q not in asked_texts:
                return PolicyDecisionResult(
                    decision="PROBE_WEAK_ANSWER_DEPTH",
                    reason=f"Technical depth scored low ({last_eval.technical_score:.1f}); probing foundational mechanism.",
                    inputs={"last_technical_score": last_eval.technical_score},
                    question_type="probe",
                    source="interview_memory",
                    difficulty=adjusted_difficulty,
                    time_limit_seconds=45 if session.mode == "pressure" else 90,
                    question_text=weak_q,
                )

    # 5. CHECK 4: Gemini Strategic Question Generation
    if answers:
        last_ans = answers[-1]
        last_q = questions_asked[-1] if questions_asked else None
        last_eval = evaluations[-1] if evaluations else None

        strat_res = decide_llm_question_strategy(
            target_role=session.target_role or "Software Engineer",
            difficulty=adjusted_difficulty,
            interview_state=sufficiency.interview_state,
            previous_question=last_q.question_text if last_q else "",
            previous_answer=last_ans.transcript if last_ans else "",
            previous_evaluation={"score": last_eval.overall_score} if last_eval else None,
            unresolved_points=memory.unresolved_points,
            resume_claims=[c.claim_text for c in claims],
            questions_already_asked=[q.question_text for q in questions_asked],
            topics_covered=memory.topics_covered,
            current_depth=sufficiency.recommended_depth,
        )

        if strat_res and strat_res.question and strat_res.question not in asked_texts:
            return PolicyDecisionResult(
                decision="LLM_ADAPTIVE_QUESTION",
                reason=strat_res.reason or "Generated strategic contextual probe via Gemini LLM.",
                inputs={
                    "llm_engine": "gemini",
                    "expected_evidence": strat_res.expected_evidence,
                    "depth_level": strat_res.depth_level,
                },
                question_type=strat_res.question_type or "probe",
                source="llm_gemini",
                difficulty=adjusted_difficulty,
                time_limit_seconds=45 if session.mode == "pressure" else 90,
                question_text=strat_res.question,
            )

    # 6. CHECK 5: High-priority unprobed resume claims
    probed_claim_ids = {q.claim_id for q in questions_asked if q.claim_id is not None}
    unprobed_claims = [
        c for c in claims
        if c.id not in probed_claim_ids and (c.probe_priority or 0.0) >= 0.55
    ]

    if unprobed_claims:
        top_claim = unprobed_claims[0]
        first_stage = "T1_FOUNDATION"
        tmpl_q = format_probe_question(top_claim.claim_text, first_stage)
        q_text = rephrase_probe_question(top_claim.claim_text, first_stage, tmpl_q)
        if q_text not in asked_texts:
            return PolicyDecisionResult(
                decision="PROBE_CLAIM",
                reason=f"Initiating probe on high-priority resume claim '{top_claim.claim_type}' (priority: {top_claim.probe_priority}).",
                inputs={
                    "claim_id": top_claim.id,
                    "claim_type": top_claim.claim_type,
                    "probe_priority": top_claim.probe_priority,
                    "ladder_stage": first_stage,
                },
                question_type="probe",
                source="resume_claim",
                claim_id=top_claim.id,
                ladder_stage=first_stage,
                difficulty=adjusted_difficulty,
                time_limit_seconds=45 if session.mode == "pressure" else 90,
                question_text=q_text,
            )

    # 7. CHECK 6: Question Bank Selection (Guarded against repetition)
    candidate_skills = []
    if session.resume_id:
        resume = db.query(models.Resume).filter(models.Resume.id == session.resume_id).first()
        if resume and resume.skills:
            try:
                candidate_skills = json.loads(resume.skills)
            except Exception:
                pass

    bank_questions = select_questions(
        db=db,
        mode=session.mode or "practice",
        difficulty=adjusted_difficulty,
        count=8,
        resume_skills=candidate_skills,
        target_role=session.target_role,
    )

    chosen_bank_q = None
    for bq in bank_questions:
        if bq["question"] not in asked_texts:
            chosen_bank_q = bq
            break

    if not chosen_bank_q:
        chosen_bank_q = bank_questions[0] if bank_questions else {
            "id": 1,
            "question": f"Explain key system design and technical tradeoffs relevant to your role as a {session.target_role}.",
            "difficulty": adjusted_difficulty,
        }

    return PolicyDecisionResult(
        decision="NEXT_BANK_QUESTION",
        reason=f"Selected {adjusted_difficulty} bank question aligned with target role '{session.target_role}'.",
        inputs={
            "adjusted_difficulty": adjusted_difficulty,
            "target_role": session.target_role,
            "turn": turn,
        },
        question_type="bank",
        source="bank",
        difficulty=adjusted_difficulty,
        time_limit_seconds=45 if session.mode == "pressure" else 90,
        question_text=chosen_bank_q["question"],
    )

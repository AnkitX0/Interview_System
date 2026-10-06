"""
backend/services/adaptive_engine.py
Deterministic Claim-Probe Ladder, Adaptive Difficulty Selection,
and Interview Decision Policy.
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

CHALLENGE_TEMPLATES: List[str] = [
    "Suppose a cascading network timeout occurs between your service and database under peak traffic. How does your design fail gracefully without taking down downstream dependencies?",
    "If your primary data store incurs silent data corruption on 2% of write requests, what monitoring alerts fire and how do you recover state without downtime?",
    "Your service's p99 latency suddenly quadruples during a release. You have 3 minutes before customer SLAs breach. What is your diagnostic runbook?",
    "Under a sudden 10x traffic spike that overwhelms your caching layer, how does your architecture prevent cache stampedes and database starvation?",
]


@dataclass
class PolicyDecisionResult:
    decision: str  # "PROBE_CLAIM", "ADVANCE_LADDER", "NEXT_BANK_QUESTION", "TRIGGER_CHALLENGE", "COMPLETE_SESSION"
    reason: str
    inputs: Dict[str, Any]
    question_type: str = "bank"  # "bank", "probe", "challenge"
    source: str = "bank"  # "bank", "resume_claim", "pressure_trigger"
    claim_id: Optional[int] = None
    ladder_stage: Optional[str] = None
    difficulty: str = "medium"
    time_limit_seconds: Optional[int] = None
    question_text: str = ""


def _deterministic_template_choice(templates: List[str], seed_str: str) -> str:
    """Deterministically picks a template from a list using MD5 hash of seed string."""
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
    return templates[h % len(templates)]


def format_probe_question(claim_text: str, stage: str) -> str:
    """Formats probe question grounded strictly in the provided claim text."""
    clean_claim = claim_text.strip()
    if clean_claim.endswith("."):
        clean_claim = clean_claim[:-1]
    templates = PROBE_TEMPLATES.get(stage, PROBE_TEMPLATES["T1_FOUNDATION"])
    tmpl = _deterministic_template_choice(templates, f"{stage}:{clean_claim}")
    return tmpl.format(claim=clean_claim)


def calculate_adjusted_difficulty(evaluations: List[models.AnswerEvaluation], current_difficulty: str) -> str:
    """
    Adjusts question bank difficulty based on rolling average score.
    Score >= 80 -> step up; Score < 60 -> step down.
    """
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
    Pure, deterministic decision policy for adaptive question selection,
    claim probing ladder, and session completion.
    """
    turn = len(questions_asked) + 1
    total_answers = len(answers)

    # 1. Check if session limit reached
    target_total = session.total_questions if session.total_questions is not None else 5
    if total_answers >= target_total:
        return PolicyDecisionResult(
            decision="COMPLETE_SESSION",
            reason=f"Target question count ({target_total}) reached.",
            inputs={"total_questions": target_total, "answers_count": total_answers},
        )

    # Calculate rolling difficulty
    adjusted_difficulty = calculate_adjusted_difficulty(evaluations, session.difficulty or "medium")

    # 2. Check for Safe Pressure Mode challenge trigger
    if session.mode == "pressure":
        challenge_count = len([q for q in questions_asked if q.question_type == "challenge"])
        last_q = questions_asked[-1] if questions_asked else None
        last_was_challenge = bool(last_q and last_q.question_type == "challenge")

        if (
            challenge_count < PRESSURE_MODE_CONFIG["max_challenges_per_session"]
            and not last_was_challenge
            and answers
        ):
            last_ans = answers[-1]
            ans_text = (last_ans.transcript or "").lower()

            challenge_cat = None
            challenge_reason = None
            if re.search(r"\b\d+(\.\d+)?%?|\b\d+(?:ms|s|m|k|mb|gb|rps|qps)\b", ans_text):
                challenge_cat = "numeric_validation"
                challenge_reason = "Pressure mode challenge: numeric claim detected in candidate response; triggering validation challenge."
            elif re.search(r"\b(i chose|i used|we chose|we used|i decided|i opted|my approach was|architecture was)\b", ans_text):
                challenge_cat = "counterexample_failure"
                challenge_reason = "Pressure mode challenge: architectural design decision stated; probing failure recovery and single point of failure."
            elif turn > 1:
                challenge_cat = "evidence_support"
                challenge_reason = "Pressure mode challenge: probing empirical evidence and operational verification."

            if challenge_cat:
                templates = PRESSURE_MODE_CONFIG["challenge_templates"].get(challenge_cat, [])
                if templates:
                    challenge_q = _deterministic_template_choice(templates, f"challenge:{session.id}:{turn}")
                    return PolicyDecisionResult(
                        decision="TRIGGER_CHALLENGE",
                        reason=challenge_reason,
                        inputs={"mode": "pressure", "challenge_category": challenge_cat, "turn": turn},
                        question_type="challenge",
                        source="pressure",
                        difficulty="hard",
                        time_limit_seconds=PRESSURE_MODE_CONFIG["default_time_limit_seconds"],
                        question_text=challenge_q,
                    )


    # 3. Check if previous question was a claim probe
    last_q = questions_asked[-1] if questions_asked else None
    if last_q and last_q.claim_id is not None and last_q.ladder_stage:
        claim_probes = [q for q in questions_asked if q.claim_id == last_q.claim_id]
        last_eval = evaluations[-1] if evaluations else None
        last_score = last_eval.overall_score if last_eval else 70.0

        # Find claim object
        target_claim = next((c for c in claims if c.id == last_q.claim_id), None)

        # Allow up to 3 ladder stages on a claim if performance is strong (score >= 65)
        if len(claim_probes) < 3 and last_score >= 65.0 and target_claim:
            curr_stage_idx = LADDER_STAGES.index(last_q.ladder_stage) if last_q.ladder_stage in LADDER_STAGES else 0
            if curr_stage_idx < len(LADDER_STAGES) - 1:
                next_stage = LADDER_STAGES[curr_stage_idx + 1]
                tmpl_q = format_probe_question(target_claim.claim_text, next_stage)
                q_text = rephrase_probe_question(target_claim.claim_text, next_stage, tmpl_q)
                return PolicyDecisionResult(
                    decision="ADVANCE_LADDER",
                    reason=f"Candidate adequately handled {last_q.ladder_stage} (score {last_score:.1f}); advancing to {next_stage}.",
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

    # 4. Check for high-priority unprobed claims
    probed_claim_ids = {q.claim_id for q in questions_asked if q.claim_id is not None}
    unprobed_claims = [
        c for c in claims
        if c.id not in probed_claim_ids and (c.probe_priority or 0.0) >= 0.55
    ]

    # Prioritize claims if available
    if unprobed_claims:
        top_claim = unprobed_claims[0]
        first_stage = "T1_FOUNDATION"
        tmpl_q = format_probe_question(top_claim.claim_text, first_stage)
        q_text = rephrase_probe_question(top_claim.claim_text, first_stage, tmpl_q)
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


    # 5. Fallback to Question Bank
    asked_texts = {q.question_text for q in questions_asked}
    candidate_skills = []
    if session.resume_id:
        resume = db.query(models.Resume).filter(models.Resume.id == session.resume_id).first()
        if resume and resume.skills:
            try:
                import json
                candidate_skills = json.loads(resume.skills)
            except Exception:
                pass

    bank_questions = select_questions(
        db=db,
        mode=session.mode or "practice",
        difficulty=adjusted_difficulty,
        count=5,
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


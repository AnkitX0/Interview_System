"""
backend/services/claim_consistency_service.py
Per-claim Resume Consistency evaluation and dynamic session consistency scoring.

Labels:
- consistent: High technical depth and verified specifics on claim ladder
- weak_support: Moderate technical depth with partial details
- low_consistency: Wording: "Low consistency between this resume claim and the answers given; this is a verification-risk indicator, not a finding of dishonesty."
- insufficient_evidence: Assigned whenever fewer than MIN_CLAIM_ANSWERS_FOR_EVALUATION (default 2) turns probed the claim.
"""

import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

import backend.models as models
from backend.config import VERIFICATION_RISK_CONFIG

MIN_CLAIM_ANSWERS_FOR_EVALUATION = 2


def evaluate_session_claim_consistency(session_id: int, db: Session) -> Dict[str, Any]:
    """
    Evaluates per-claim consistency across all probed claims in an interview session.
    Persists results in claim_consistency table and derives session-level score.
    """
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id
    ).first()

    if not session or not session.resume_id:
        return {
            "consistency_source": "legacy",
            "derived_score": None,
            "claim_records": []
        }

    claims = db.query(models.ResumeClaim).filter(
        models.ResumeClaim.resume_id == session.resume_id
    ).all()

    if not claims:
        return {
            "consistency_source": "legacy",
            "derived_score": None,
            "claim_records": []
        }

    # Query all probed questions for this session
    probed_questions = db.query(models.InterviewQuestion).filter(
        models.InterviewQuestion.session_id == session_id,
        models.InterviewQuestion.claim_id.isnot(None)
    ).all()

    # Group questions by claim_id
    questions_by_claim: Dict[int, List[models.InterviewQuestion]] = {}
    for q in probed_questions:
        questions_by_claim.setdefault(q.claim_id, []).append(q)

    # Delete existing claim consistency records for this session to allow re-runs
    db.query(models.ClaimConsistency).filter(
        models.ClaimConsistency.session_id == session_id
    ).delete()

    claim_records = []
    evaluated_scores: List[float] = []

    for claim in claims:
        questions = questions_by_claim.get(claim.id, [])
        if not questions:
            # Not probed at all -> insufficient_evidence
            label = "insufficient_evidence"
            evidence = ["Claim was not probed during this interview session."]
            answers_considered = 0
            claim_score = None
        else:
            # Find answers corresponding to these questions
            q_ids = [q.id for q in questions]
            answers = db.query(models.InterviewAnswer).filter(
                models.InterviewAnswer.session_id == session_id,
                models.InterviewAnswer.question_id.in_(q_ids)
            ).all()

            answers_considered = len(answers)

            if answers_considered < MIN_CLAIM_ANSWERS_FOR_EVALUATION:
                label = "insufficient_evidence"
                evidence = [
                    f"Only {answers_considered} turn(s) probed this claim; minimum {MIN_CLAIM_ANSWERS_FOR_EVALUATION} required for consistency determination."
                ]
                claim_score = None
            else:
                # Retrieve answer evaluations
                a_ids = [a.id for a in answers]
                evals = db.query(models.AnswerEvaluation).filter(
                    models.AnswerEvaluation.answer_id.in_(a_ids)
                ).all()

                turn_scores = [ev.overall_score for ev in evals if ev and ev.overall_score is not None]
                avg_score = sum(turn_scores) / len(turn_scores) if turn_scores else 70.0

                vrisk_scores = [ev.verification_risk_score for ev in evals if ev and ev.verification_risk_score is not None]
                avg_vrisk = sum(vrisk_scores) / len(vrisk_scores) if vrisk_scores else 30.0

                # Check technology mentions in transcripts
                techs = claim.technologies if isinstance(claim.technologies, list) else []
                if isinstance(claim.technologies, str):
                    try:
                        techs = json.loads(claim.technologies)
                    except Exception:
                        techs = []

                all_transcripts = " ".join((a.transcript or "").lower() for a in answers)
                tech_mentions = [t for t in techs if t.lower() in all_transcripts]

                evidence = []
                if tech_mentions:
                    evidence.append(f"Referenced declared technologies: {', '.join(tech_mentions)}.")
                elif techs:
                    evidence.append("Declared technologies were not specifically articulated in responses.")

                if avg_vrisk > 55.0:
                    evidence.append("Elevated verification risk observed on probe responses.")

                # Determine label
                if avg_score >= 70.0 and avg_vrisk <= 35.0:
                    label = "consistent"
                    evidence.append(f"Strong response depth (average score {round(avg_score, 1)}%) on claim ladder.")
                    claim_score = min(100.0, avg_score + 5.0)
                elif avg_score >= 50.0 and avg_vrisk <= 55.0:
                    label = "weak_support"
                    evidence.append(f"Partial technical depth (average score {round(avg_score, 1)}%) on claim ladder.")
                    claim_score = 65.0
                else:
                    label = "low_consistency"
                    evidence.append("Low consistency between this resume claim and the answers given; this is a verification-risk indicator, not a finding of dishonesty.")
                    claim_score = 40.0

                evaluated_scores.append(claim_score)

        record = models.ClaimConsistency(
            session_id=session_id,
            claim_id=claim.id,
            label=label,
            evidence=evidence,
            answers_considered=answers_considered
        )
        db.add(record)
        claim_records.append({
            "claim_id": claim.id,
            "claim_text": claim.claim_text,
            "claim_type": claim.claim_type,
            "label": label,
            "evidence": evidence,
            "answers_considered": answers_considered,
            "score": claim_score
        })

    db.flush()

    if evaluated_scores:
        derived_score = round(sum(evaluated_scores) / len(evaluated_scores), 1)
        consistency_source = "claim_level"
    else:
        derived_score = None
        consistency_source = "legacy"

    return {
        "consistency_source": consistency_source,
        "derived_score": derived_score,
        "claim_records": claim_records
    }

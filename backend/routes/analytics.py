import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

import backend.models as models
from backend.database import get_db
from backend.schemas.schemas import ImproveAnswerRequest
from backend.services.auth_service import get_current_user
from backend.services.answer_improvement_service import improve_interview_answer
from backend.services.scoring_engine import evaluate_rubric_for_answer
from backend.services.timeline_service import generate_session_timeline
from backend.services.weakness_diagnosis_engine import diagnose_session_weaknesses, get_performance_dimension_model
from backend.services.recurring_weakness_service import aggregate_user_weaknesses, get_recurring_weaknesses
from backend.services.velocity_service import calculate_improvement_velocity
from backend.services.practice_recommendation_engine import select_next_practice
from backend.services.readiness_engine import compute_longitudinal_readiness
from backend.config import VERIFICATION_RISK_CONFIG

router = APIRouter(tags=["Analytics & Reports"])



# =========================
# GET SESSION REPORT
# =========================
@router.get("/report/latest")
def get_latest_session_report(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.user_id == user.id
    ).order_by(models.InterviewSession.id.desc()).first()

    if not session:
        raise HTTPException(status_code=404, detail="No interview sessions found")

    return get_session_report(session.id, user=user, db=db)


@router.get("/report/{session_id}")
def get_session_report(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    score_record = db.query(models.SessionScore).filter(
        models.SessionScore.session_id == session_id
    ).first()

    behavioral = db.query(models.BehavioralMetrics).filter(
        models.BehavioralMetrics.session_id == session_id
    ).first()

    answers = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == session_id
    ).all()

    answer_evals = []
    for ans in answers:
        ev = db.query(models.AnswerEvaluation).filter(
            models.AnswerEvaluation.answer_id == ans.id
        ).first()

        strengths = []
        weaknesses = []
        missing_concepts = []
        suggestions = []

        if ev:
            try:
                strengths = json.loads(ev.strengths or "[]")
                weaknesses = json.loads(ev.weaknesses or "[]")
                missing_concepts = json.loads(ev.missing_concepts or "[]")
                suggestions = json.loads(ev.suggestions or "[]")
            except Exception:
                pass

        # Reconstruct structured dimensions
        ev_eval = evaluate_rubric_for_answer(
            transcript=ans.transcript or "",
            question_text=ans.question_text or "",
            category=session.mode or "Technical",
            response_time=ans.response_time or 0.0,
            wpm=ans.wpm or 0.0,
            filler_count=ans.filler_count or 0
        )

        # Query voice metrics if available
        vm = db.query(models.VoiceMetrics).filter(
            models.VoiceMetrics.answer_id == ans.id
        ).first()

        vm_data = None
        if vm:
            vm_data = {
                "speech_source": vm.speech_source,
                "words_per_minute": {
                    "value": vm.words_per_minute,
                    "interpretation": f"{vm.words_per_minute} WPM pacing." if vm.words_per_minute is not None else "Not measured (typed answer or audio timing unavailable).",
                    "recommended_action": "Target 120-160 WPM for standard conversational pacing.",
                },
                "filler_words": {
                    "value": vm.filler_word_count,
                    "interpretation": f"{vm.filler_word_count} verbal filler words recorded." if vm.filler_word_count is not None else "Not measured.",
                    "recommended_action": "Deliberately pause rather than using verbal fillers.",
                },
                "pause_metrics": {
                    "pause_count": vm.pause_count,
                    "avg_pause_duration": vm.avg_pause_duration,
                    "longest_pause": vm.longest_pause,
                    "silence_ratio": vm.silence_ratio,
                    "interpretation": f"{vm.pause_count} pauses (average {vm.avg_pause_duration}s, longest {vm.longest_pause}s, silence ratio {round((vm.silence_ratio or 0) * 100, 1)}%). Approximate, based on speech-recognition timing." if vm.pause_count is not None else "Not measured (typed answer or speech timing unavailable).",
                    "recommended_action": "Maintain conversational cadence with planned structural pauses.",
                },
                "vocabulary_diversity": {
                    "value": vm.vocabulary_diversity_score,
                    "interpretation": f"Unique words ratio of {vm.vocabulary_diversity_score}%." if vm.vocabulary_diversity_score is not None else "Not measured: answer too brief for diversity evaluation.",
                    "recommended_action": "Incorporate diverse domain terminology.",
                },
            }

        iq = db.query(models.InterviewQuestion).filter(
            models.InterviewQuestion.session_id == session_id,
            models.InterviewQuestion.id == ans.question_id
        ).first()
        if not iq:
            iq = db.query(models.InterviewQuestion).filter(
                models.InterviewQuestion.session_id == session_id,
                models.InterviewQuestion.question_text == ans.question_text
            ).first()

        answer_evals.append({
            "answer_id": ans.id,
            "question_id": ans.question_id,
            "question_text": ans.question_text or "Question",
            "question_type": iq.question_type if iq else "technical",
            "source": iq.source if iq else "bank",
            "ladder_stage": iq.ladder_stage if iq else None,
            "generated_reason": iq.generated_reason if iq else None,
            "transcript": ans.transcript or "",
            "response_time": ans.response_time or 0.0,
            "wpm": ans.wpm or 0.0,
            "filler_count": ans.filler_count or 0,
            "voice_metrics": vm_data,
            "overall_score": ev.overall_score if ev else 70.0,
            "structure_score": ev.structure_score if ev else 70.0,
            "technical_score": ev.technical_score if ev else 70.0,
            "reasoning_score": ev.reasoning_score if ev else 70.0,
            "star_score": ev.star_score if ev else 70.0,
            "consistency_score": ev.consistency_score if ev else 75.0,
            "dimensions": ev_eval.get("dimensions", {}),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_concepts": missing_concepts,
            "suggestions": suggestions,
            "engine_used": (ev.engine_used if ev and hasattr(ev, 'engine_used') and ev.engine_used else "rubric"),
            "prompt_version": (ev.prompt_version if ev and hasattr(ev, 'prompt_version') and ev.prompt_version else "v1.0"),
            "verification_risk": {
                "score": ev.verification_risk_score if ev else None,
                "level": ev.verification_risk_level if ev and ev.verification_risk_level else "not_computed",
                "evidence": ev.verification_risk_evidence if ev and ev.verification_risk_evidence else [],
                "explanation": ev.verification_risk_explanation if ev else None,
                "disclaimer": VERIFICATION_RISK_CONFIG["disclaimer"],
            }
        })


    # Session scoring values
    readiness = score_record.readiness_score if score_record else 72.0
    comm = score_record.communication_score if score_record else 75.0
    tech = score_record.technical_score if score_record else 70.0
    deliv = score_record.behavioral_score if score_record else None
    cons = score_record.resume_consistency_score if score_record else 75.0
    strongest = score_record.strongest_category if score_record else "Communication"
    weakest = score_record.weakest_category if score_record else "Technical"

    weights_used = {}
    if score_record and score_record.weights_used:
        try:
            weights_used = json.loads(score_record.weights_used)
        except Exception:
            pass

    if weights_used:
        delivery_measured = weights_used.get("delivery", 0.0) > 0.0
    else:
        delivery_measured = deliv is not None

    if not delivery_measured:
        deliv = None

    if not weights_used:
        weights_used = (
            {"communication": 0.30, "technical": 0.30, "delivery": 0.20, "resume_consistency": 0.20}
            if delivery_measured
            else {"communication": 0.375, "technical": 0.375, "delivery": 0.0, "resume_consistency": 0.25}
        )

    insights = []
    if score_record and score_record.insights:
        try:
            insights = json.loads(score_record.insights)
        except Exception:
            insights = [score_record.insights]

    if not insights:
        insights = [
            f"Strongest performance observed in {strongest} ({comm}%).",
            f"Opportunity to sharpen {weakest} depth and structural examples.",
        ]
        if delivery_measured:
            insights.append("Integrate quantifiable outcomes (numbers, scale, percentages) into every behavioral and system response.")
        else:
            insights.append("Not measured: camera was off. Readiness score was computed from 3 dimensions (Communication 37.5%, Technical 37.5%, Resume Consistency 25%).")

    status_label = "Job-Ready Candidate" if readiness >= 80 else ("Near Interview-Ready" if readiness >= 65 else "Requires Targeted Practice")

    radar_data = [
        {"subject": "Communication", "score": comm, "fullMark": 100},
        {"subject": "Technical Depth", "score": tech, "fullMark": 100},
        {"subject": "Resume Consistency", "score": cons, "fullMark": 100}
    ]
    if delivery_measured and deliv is not None:
        radar_data.append({"subject": "Delivery & Stability", "score": deliv, "fullMark": 100})

    eye_val = behavioral.eye_contact_percent if behavioral else None
    blink_val = behavioral.blink_rate if behavioral else None
    pause_val = behavioral.pause_rate if behavioral else None

    delivery_metrics_dict = {
        "delivery_measured": delivery_measured,
        "visual_centering_percent": eye_val,
        "eye_contact_percent": eye_val,
        "blink_rate": blink_val,
        "pause_rate": pause_val,
        "note": "Measured" if delivery_measured else "Not measured: camera was off"
    }

    decisions = db.query(models.InterviewDecision).filter(
        models.InterviewDecision.session_id == session_id
    ).order_by(models.InterviewDecision.turn.asc()).all()

    decision_log = []
    for d in decisions:
        parsed_inputs = {}
        if d.inputs:
            try:
                parsed_inputs = json.loads(d.inputs) if isinstance(d.inputs, str) else d.inputs
            except Exception:
                pass
        decision_log.append({
            "turn": d.turn,
            "decision": d.decision,
            "reason": d.reason,
            "inputs": parsed_inputs,
            "timestamp": d.created_at.isoformat() if d.created_at else None,
        })

    # Query per-claim consistency records
    claim_cons_list = db.query(models.ClaimConsistency).filter(
        models.ClaimConsistency.session_id == session_id
    ).all()
    claim_records = []
    for cc in claim_cons_list:
        claim_obj = db.query(models.ResumeClaim).filter(models.ResumeClaim.id == cc.claim_id).first()
        evidence_list = []
        if cc.evidence:
            try:
                evidence_list = json.loads(cc.evidence) if isinstance(cc.evidence, str) else cc.evidence
            except Exception:
                pass
        claim_records.append({
            "claim_id": cc.claim_id,
            "claim_text": claim_obj.claim_text if claim_obj else "Resume claim",
            "claim_type": claim_obj.claim_type if claim_obj else "general",
            "label": cc.label,
            "evidence": evidence_list,
            "answers_considered": cc.answers_considered,
        })

    consistency_source = (
        score_record.consistency_source
        if score_record and hasattr(score_record, "consistency_source") and score_record.consistency_source
        else "legacy"
    )

    return {
        "session_id": session.id,
        "mode": session.mode,
        "difficulty": session.difficulty,
        "target_role": session.target_role,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "readiness_score": readiness,
        "status_label": status_label,
        "delivery_measured": delivery_measured,
        "weights_used": weights_used,
        "consistency_source": consistency_source,
        "subscores": {
            "communication": comm,
            "technical": tech,
            "delivery": deliv,
            "delivery_measured": delivery_measured,
            "behavioral": deliv,
            "resume_consistency": cons,
            "consistency_source": consistency_source,
            "weights_used": weights_used
        },
        "insights": {
            "strongest_category": strongest,
            "weakest_category": weakest,
            "top_improvements": insights
        },
        "delivery_metrics": delivery_metrics_dict,
        "behavioral_metrics": delivery_metrics_dict,
        "radar_data": radar_data,
        "answers": answer_evals,
        "decision_log": decision_log,
        "claim_consistency": claim_records,
        "timeline": generate_session_timeline(session.id, db),
        "performance_dimensions": get_performance_dimension_model(session.id, db),
        "session_weaknesses": diagnose_session_weaknesses(session.id, db),
        "recurring_weaknesses": get_recurring_weaknesses(user.id, db),
        "next_practice": select_next_practice(user.id, db, source_session_id=session.id, save_to_db=False)
    }




# =========================
# GET PROGRESS HISTORY
# =========================
@router.get("/progress")
def get_progress_data(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(models.InterviewSession).filter(
        models.InterviewSession.user_id == user.id
    ).order_by(
        models.InterviewSession.id.asc()
    ).all()

    if not sessions:
        return {
            "total_interviews": 0,
            "average_readiness_score": 0,
            "best_score": 0,
            "latest_score": 0,
            "improvement_percentage": 0,
            "weakest_category": "N/A",
            "sessions": [],
            "trend": []
        }

    session_list = []
    trend_data = []
    scores = []

    for idx, s in enumerate(sessions):
        score_rec = db.query(models.SessionScore).filter(
            models.SessionScore.session_id == s.id
        ).first()

        readiness = score_rec.readiness_score if (score_rec and score_rec.readiness_score) else (score_rec.behavioral_score if score_rec else 70.0)
        scores.append(readiness)

        item = {
            "session_id": s.id,
            "attempt": f"Session #{idx + 1}",
            "date": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else f"Attempt {idx + 1}",
            "mode": (s.mode or "practice").title(),
            "difficulty": (s.difficulty or "medium").title(),
            "readiness_score": round(readiness, 1),
            "status": s.status or "completed",
            "communication_score": score_rec.communication_score if score_rec else readiness,
            "technical_score": score_rec.technical_score if score_rec else readiness,
            "behavioral_score": score_rec.behavioral_score if score_rec else readiness,
        }
        session_list.append(item)
        trend_data.append({
            "attempt": f"#{idx + 1}",
            "readiness_score": round(readiness, 1),
            "communication_score": item["communication_score"],
            "technical_score": item["technical_score"],
            "behavioral_score": item["behavioral_score"]
        })

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    best_score = round(max(scores), 1) if scores else 0
    latest_score = round(scores[-1], 1) if scores else 0
    first_score = scores[0] if scores else 0
    improvement = round(((latest_score - first_score) / max(first_score, 1)) * 100, 1) if len(scores) > 1 else 0.0
    longitudinal = compute_longitudinal_readiness(user.id, db)
    user_weaknesses = aggregate_user_weaknesses(user.id, db)
    velocity = calculate_improvement_velocity(user.id, db)
    next_practice = select_next_practice(user.id, db, save_to_db=False)

    return {
        "total_interviews": len(sessions),
        "average_readiness_score": avg_score,
        "best_score": best_score,
        "latest_score": latest_score,
        "improvement_percentage": improvement,
        "weakest_category": longitudinal.get("weakest_dimension", "Technical Depth"),
        "strongest_category": longitudinal.get("strongest_dimension", "Communication"),
        "sessions": list(reversed(session_list)),
        "trend": trend_data,
        "longitudinal_readiness": longitudinal,
        "recurring_weaknesses": user_weaknesses,
        "improvement_velocity": velocity,
        "next_practice": next_practice
    }


# =========================
# FIX MY ANSWER ENDPOINTS
# =========================
@router.post("/answer/{answer_id}/improve")
def improve_answer_by_id(
    answer_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    answer_rec = db.query(models.InterviewAnswer).join(
        models.InterviewSession
    ).filter(
        models.InterviewAnswer.id == answer_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not answer_rec:
        raise HTTPException(status_code=404, detail="Answer not found")

    question = answer_rec.question_text or "Interview Question"
    transcript = answer_rec.transcript or ""

    improved_data = improve_interview_answer(
        question=question,
        original_answer=transcript
    )

    return improved_data


@router.post("/answer/improve")
def improve_custom_answer(
    data: ImproveAnswerRequest,
    user: models.User = Depends(get_current_user)
):
    if not data.answer.strip():
        raise HTTPException(status_code=400, detail="Answer text cannot be empty")

    improved_data = improve_interview_answer(
        question=data.question,
        original_answer=data.answer,
        target_role=data.target_role or "Software Engineer"
    )

    return improved_data


import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

import backend.models as models
from backend.database import get_db
from backend.crud import calculate_behavioral_score, calculate_delivery_score
from backend.schemas.schemas import (
    AnswerInput,
    FollowUpRequest,
    StartInterviewRequest,
    BehavioralInput,
    CompleteInterviewRequest,
    SkipQuestionRequest,
)
from backend.services.auth_service import get_current_user
from backend.services.evaluation_engine import evaluate_answer
from backend.services.followup_generator import generate_followup
from backend.services.scoring_engine import calculate_session_score
from backend.services.question_selector import select_questions
from backend.services.voice_service import compute_voice_metrics
from backend.services.adaptive_engine import decide_next_question
from backend.services.verification_risk import compute_verification_risk
from backend.services.claim_consistency_service import evaluate_session_claim_consistency
from backend.services.visual_metrics_service import (
    store_answer_visual_metrics,
    evaluate_visual_quality_gate,
)

router = APIRouter(prefix="/interview", tags=["Interview"])




# =========================
# START INTERVIEW
# =========================
@router.post("/start")
def start_interview(
    data: StartInterviewRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    mode = data.mode or "practice"
    difficulty = data.difficulty or "medium"
    number_of_questions = data.number_of_questions or 3
    target_role = data.target_role or "Software Engineer"

    resume_skills = []
    if data.resume_id:
        resume = db.query(models.Resume).filter(
            models.Resume.id == data.resume_id,
            models.Resume.user_id == user.id
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        if resume and resume.skills:
            try:
                resume_skills = json.loads(resume.skills)
            except Exception:
                resume_skills = [s.strip() for s in resume.skills.split(",") if s.strip()]

    policy_name = data.session_policy.upper() if data.session_policy else (
        "DRILL" if number_of_questions <= 3 else ("SHORT" if number_of_questions <= 5 else ("STANDARD" if number_of_questions <= 8 else "DEEP"))
    )
    q_mode = (data.question_mode or "ADAPTIVE").upper()

    session = models.InterviewSession(
        user_id=user.id,
        mode=mode,
        difficulty=difficulty,
        target_role=target_role,
        resume_id=data.resume_id,
        total_questions=number_of_questions,
        question_mode=q_mode,
        session_policy=policy_name,
        interview_state="STARTING",
        current_question_index=0,
        followup_count=0,
        status="in_progress"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    # Select resume-aware dynamic questions
    selected_questions = select_questions(
        db=db,
        mode=mode,
        difficulty=difficulty,
        count=number_of_questions,
        resume_skills=resume_skills,
        target_role=target_role
    )

    time_limit = 45 if mode == "pressure" else 90
    for q in selected_questions:
        q["time_limit_seconds"] = time_limit
        q["caption"] = "Core Interview Question"

    init_decision = models.InterviewDecision(
        session_id=session.id,
        turn=1,
        decision="START_SESSION",
        reason=f"Interview started in {mode} mode ({difficulty}) for role '{target_role}'. Policy: {policy_name} ({q_mode}). Time limit: {time_limit}s.",
        inputs={"mode": mode, "difficulty": difficulty, "target_role": target_role, "session_policy": policy_name, "question_mode": q_mode, "time_limit_seconds": time_limit}
    )
    db.add(init_decision)
    db.commit()

    return {
        "session_id": session.id,
        "mode": mode,
        "difficulty": difficulty,
        "target_role": target_role,
        "question_mode": q_mode,
        "session_policy": policy_name,
        "total_questions": len(selected_questions),
        "questions": selected_questions
    }


# =========================
# SWITCH INTERVIEW MODE (PRESSURE -> PRACTICE)
# =========================
@router.post("/{session_id}/switch-mode")
def switch_interview_mode(
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

    session.mode = "technical"
    decision_rec = models.InterviewDecision(
        session_id=session.id,
        turn=session.current_question_index + 1,
        decision="SWITCH_TO_PRACTICE",
        reason="Candidate requested mid-session switch from Safe Pressure Mode to Practice Mode. Time limit relaxed to 90s.",
        inputs={"previous_mode": "pressure", "new_mode": "technical"}
    )
    db.add(decision_rec)
    db.commit()

    return {
        "session_id": session.id,
        "mode": "technical",
        "time_limit_seconds": 90,
        "message": "Switched to practice mode successfully."
    }



# =========================
# HISTORY, LATEST & ALL SESSIONS
# =========================
@router.get("/history")
def get_interview_history(
    page: int = 1,
    limit: int = 10,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Paginated list of interview sessions for the current user, newest first."""
    offset = max(0, (page - 1) * limit)
    total = db.query(models.InterviewSession).filter(
        models.InterviewSession.user_id == user.id
    ).count()

    sessions = db.query(models.InterviewSession).filter(
        models.InterviewSession.user_id == user.id
    ).order_by(
        models.InterviewSession.id.desc()
    ).offset(offset).limit(limit).all()

    items = []
    for s in sessions:
        score = db.query(models.SessionScore).filter(
            models.SessionScore.session_id == s.id
        ).first()
        items.append({
            "session_id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "mode": s.mode,
            "difficulty": s.difficulty,
            "target_role": s.target_role,
            "status": s.status,
            "readiness_score": score.readiness_score if score else None,
            "delivery_score": score.behavioral_score if score else None,
            "communication_score": score.communication_score if score else None,
            "technical_score": score.technical_score if score else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/latest")
def get_latest_session(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    latest = db.query(models.SessionScore).join(
        models.InterviewSession
    ).filter(
        models.InterviewSession.user_id == user.id
    ).order_by(
        models.SessionScore.id.desc()
    ).first()

    if not latest:
        return {"message": "No sessions yet"}

    return {
        "session_id": latest.session_id,
        "behavioral_score": latest.behavioral_score,
        "readiness_score": latest.readiness_score or latest.behavioral_score
    }


@router.get("/all")
def get_all_sessions(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(models.SessionScore).join(
        models.InterviewSession
    ).filter(
        models.InterviewSession.user_id == user.id
    ).all()
    result = []
    for index, s in enumerate(sessions):
        result.append({
            "attempt": str(index + 1),
            "behavioral_score": s.behavioral_score,
            "readiness_score": s.readiness_score or s.behavioral_score
        })
    return result


# =========================
# GET SESSION STATUS / DETAILS
# =========================
@router.get("/{session_id}")
def get_session_details(
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

    answers = db.query(models.InterviewAnswer).filter(models.InterviewAnswer.session_id == session_id).all()
    score = db.query(models.SessionScore).filter(models.SessionScore.session_id == session_id).first()

    return {
        "session_id": session.id,
        "mode": session.mode,
        "difficulty": session.difficulty,
        "target_role": session.target_role,
        "question_mode": getattr(session, "question_mode", "ADAPTIVE"),
        "session_policy": getattr(session, "session_policy", "STANDARD"),
        "interview_state": getattr(session, "interview_state", "STARTING"),
        "total_questions": session.total_questions,
        "current_question_index": session.current_question_index,
        "status": session.status,
        "answers_count": len(answers),
        "readiness_score": score.readiness_score if score else None
    }


# =========================
# SUBMIT ANSWER
# =========================
@router.post("/answer")
@router.post("/{session_id}/answer")
def submit_answer(
    data: AnswerInput,
    session_id: Optional[int] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_session_id = session_id or data.session_id

    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == target_session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Retrieve candidate resume skills if available
    resume_skills = []
    if session.resume_id:
        resume = db.query(models.Resume).filter(models.Resume.id == session.resume_id).first()
        if resume and resume.skills:
            try:
                resume_skills = json.loads(resume.skills)
            except Exception:
                pass

    question_text = data.question_text
    if not question_text and data.question_id:
        q_record = db.query(models.QuestionBank).filter(models.QuestionBank.id == data.question_id).first()
        if q_record:
            question_text = q_record.question_text

    raw_transcript = (data.transcript or "").strip()
    resp_time = max(0.0, data.response_time or 0.0)
    dur_seconds = max(0.0, data.duration_seconds or resp_time)

    # Safe WPM calculation guarded against zero/negative duration
    if data.wpm is not None and data.wpm > 0.0:
        safe_wpm = data.wpm
    elif dur_seconds > 0.0:
        words_count = len(raw_transcript.split())
        dur_minutes = dur_seconds / 60.0
        safe_wpm = round(words_count / dur_minutes, 1) if dur_minutes > 0.0 else 0.0
    else:
        safe_wpm = 0.0

    answer = models.InterviewAnswer(
        session_id=target_session_id,
        question_id=data.question_id,
        question_text=question_text or "Interview Question",
        transcript=raw_transcript,
        response_time=resp_time,
        duration_seconds=dur_seconds,
        wpm=safe_wpm,
        filler_count=max(0, data.filler_count or 0)
    )

    db.add(answer)
    db.commit()
    db.refresh(answer)

    # Evaluate answer using structured rubric
    category = session.mode if session.mode in ["Technical", "HR", "Behavioral", "Pressure"] else "Technical"
    evaluation = evaluate_answer(
        transcript=raw_transcript,
        question_text=question_text or "",
        category=category,
        resume_skills=resume_skills,
        response_time=resp_time,
        wpm=safe_wpm,
        filler_count=max(0, data.filler_count or 0)
    )

    # Fetch prior transcripts for repetition comparison
    prev_transcripts = [
        a.transcript for a in db.query(models.InterviewAnswer).filter(
            models.InterviewAnswer.session_id == session.id,
            models.InterviewAnswer.id != answer.id
        ).all() if a.transcript
    ]

    v_risk = compute_verification_risk(
        transcript=raw_transcript,
        previous_answers=prev_transcripts,
        question_text=question_text or ""
    )

    eval_record = models.AnswerEvaluation(
        answer_id=answer.id,
        structure_score=evaluation["structure_score"],
        clarity_score=evaluation["clarity_score"],
        depth_score=evaluation["depth_score"],
        technical_score=evaluation["technical_score"],
        reasoning_score=evaluation["reasoning_score"],
        star_score=evaluation["star_score"],
        consistency_score=evaluation["consistency_score"],
        overall_score=evaluation["overall_score"],
        strengths=json.dumps(evaluation["strengths"]),
        weaknesses=json.dumps(evaluation["weaknesses"]),
        missing_concepts=json.dumps(evaluation["missing_concepts"]),
        suggestions=json.dumps(evaluation["suggestions"]),
        engine_used=evaluation.get("engine_used", "rubric"),
        prompt_version=evaluation.get("prompt_version", "v1.0"),
        verification_risk_score=v_risk.get("score"),
        verification_risk_level=v_risk.get("level"),
        verification_risk_evidence=v_risk.get("evidence", []),
        verification_risk_explanation=v_risk.get("explanation"),
    )

    db.add(eval_record)

    # Compute and persist voice & speech cadence metrics
    voice_metrics = compute_voice_metrics(
        transcript=raw_transcript,
        duration_seconds=dur_seconds,
        speech_segments=data.speech_segments,
        speech_source=data.speech_source or "speech",
    )

    vm_raw = voice_metrics["raw"]
    vm_record = models.VoiceMetrics(
        answer_id=answer.id,
        words_per_minute=vm_raw["words_per_minute"],
        filler_word_count=vm_raw["filler_word_count"],
        avg_pause_duration=vm_raw["avg_pause_duration"],
        longest_pause=vm_raw["longest_pause"],
        pause_count=vm_raw["pause_count"],
        silence_ratio=vm_raw["silence_ratio"],
        vocabulary_diversity_score=vm_raw["vocabulary_diversity_score"],
        speech_source=vm_raw["speech_source"],
    )
    db.add(vm_record)

    # Persist extended visual metrics if provided
    visual_record = store_answer_visual_metrics(answer.id, data, db)
    visual_info = None
    if visual_record:
        v_dict = {
            "head_alignment_percent": visual_record.head_alignment_percent,
            "blink_rate": visual_record.blink_rate,
            "head_movement_variance": visual_record.head_movement_variance,
            "face_visibility_ratio": visual_record.face_visibility_ratio,
            "head_shift_count": visual_record.head_shift_count,
            "frames_sampled": visual_record.frames_sampled,
        }
        gate_res = evaluate_visual_quality_gate(v_dict)
        visual_info = {
            **v_dict,
            "quality_status": gate_res["quality_status"],
            "is_usable": gate_res["is_usable"],
            "quality_reason": gate_res["reason"],
        }

    session.current_question_index += 1
    session.followup_count = 0
    db.commit()

    return {
        "message": "Answer stored and evaluated successfully",
        "answer_id": answer.id,
        "score": evaluation["overall_score"],
        "dimensions": evaluation.get("dimensions", {}),
        "structure": evaluation.get("structure"),
        "technical": evaluation.get("technical"),
        "reasoning": evaluation.get("reasoning"),
        "star": evaluation.get("star"),
        "consistency": evaluation.get("consistency"),
        "engine_used": evaluation.get("engine_used", "rubric"),
        "prompt_version": evaluation.get("prompt_version", "v1.0"),
        "voice_metrics": voice_metrics,
        "visual_metrics": visual_info,
        "verification_risk": v_risk,
        "structure_score": evaluation["structure_score"],
        "technical_score": evaluation["technical_score"],
        "reasoning_score": evaluation["reasoning_score"],
        "star_score": evaluation["star_score"],
        "consistency_score": evaluation["consistency_score"],
        "strengths": evaluation["strengths"],
        "weaknesses": evaluation["weaknesses"],
        "missing_concepts": evaluation["missing_concepts"],
        "suggestions": evaluation["suggestions"]
    }


# =========================
# SKIP QUESTION
# =========================
@router.post("/skip")
@router.post("/{session_id}/skip")
def skip_question(
    data: Optional[SkipQuestionRequest] = None,
    session_id: Optional[int] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_session_id = session_id or (data.session_id if data else None)
    if not target_session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == target_session_id,
        models.InterviewSession.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    q_id = data.question_id if data else None
    q_text = data.question_text if data else None

    if not q_text and q_id:
        q_record = db.query(models.QuestionBank).filter(models.QuestionBank.id == q_id).first()
        if not q_record:
            q_record = db.query(models.InterviewQuestion).filter(models.InterviewQuestion.id == q_id).first()
        if q_record:
            q_text = getattr(q_record, "question_text", None) or getattr(q_record, "question", None)

    if not q_text:
        last_q = db.query(models.InterviewQuestion).filter(
            models.InterviewQuestion.session_id == target_session_id
        ).order_by(models.InterviewQuestion.sequence_order.desc()).first()
        if last_q:
            q_text = last_q.question_text
            q_id = q_id or last_q.id

    question_text = q_text or "Interview Question"

    # 1. Persist skipped turn
    answer = models.InterviewAnswer(
        session_id=target_session_id,
        question_id=q_id,
        question_text=question_text,
        transcript="[SKIPPED] Candidate chose to skip this question.",
        response_time=0.0,
        duration_seconds=0.0,
        wpm=0.0,
        filler_count=0
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    # 2. Persist safe evaluation for skipped turn
    eval_record = models.AnswerEvaluation(
        answer_id=answer.id,
        structure_score=40.0,
        clarity_score=40.0,
        depth_score=30.0,
        technical_score=40.0,
        reasoning_score=40.0,
        star_score=40.0,
        consistency_score=50.0,
        overall_score=40.0,
        strengths=json.dumps([]),
        weaknesses=json.dumps(["Candidate skipped question; evidence was not provided."]),
        missing_concepts=json.dumps(["Evidence not obtained"]),
        suggestions=json.dumps(["Review foundational concepts for this topic to prepare for live interviews."]),
        engine_used="skipped",
        prompt_version="skipped-v1",
        verification_risk_score=None,
        verification_risk_level="not_computed",
        verification_risk_evidence=[],
        verification_risk_explanation="Skipped question - verification risk not computed.",
    )
    db.add(eval_record)

    # 3. Log decision: CANDIDATE_SKIPPED
    decision_rec = models.InterviewDecision(
        session_id=session.id,
        turn=session.current_question_index + 1,
        decision="CANDIDATE_SKIPPED",
        reason="Candidate skipped question. Recorded as evidence not obtained.",
        inputs={
            "question_text": question_text,
            "skipped": True,
            "candidate_diversion": False,
            "reason": (data.reason if data else "candidate_skipped") or "candidate_skipped",
        }
    )
    db.add(decision_rec)
    session.current_question_index += 1
    session.followup_count = 0
    db.commit()

    # Ensure skipped question is in InterviewQuestion table for InterviewMemory and repetition prevention
    existing_q = db.query(models.InterviewQuestion).filter(
        models.InterviewQuestion.session_id == target_session_id,
        models.InterviewQuestion.question_text == question_text
    ).first()
    if not existing_q:
        prior_qs = db.query(models.InterviewQuestion).filter(
            models.InterviewQuestion.session_id == target_session_id
        ).all()
        skipped_q_rec = models.InterviewQuestion(
            session_id=session.id,
            sequence_order=len(prior_qs) + 1,
            question_text=question_text,
            question_type="bank",
            source="bank",
            generated_reason="Candidate skipped question.",
        )
        db.add(skipped_q_rec)
        db.commit()

    # 4. Generate next question adaptively
    answers = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == target_session_id
    ).order_by(models.InterviewAnswer.id.asc()).all()

    evaluations = []
    for a in answers:
        ev = db.query(models.AnswerEvaluation).filter(
            models.AnswerEvaluation.answer_id == a.id
        ).first()
        if ev:
            evaluations.append(ev)

    claims = []
    if session.resume_id:
        claims = db.query(models.ResumeClaim).filter(
            models.ResumeClaim.resume_id == session.resume_id
        ).order_by(models.ResumeClaim.probe_priority.desc()).all()

    questions_asked = db.query(models.InterviewQuestion).filter(
        models.InterviewQuestion.session_id == target_session_id
    ).order_by(models.InterviewQuestion.sequence_order.asc()).all()

    decision_res = decide_next_question(
        session=session,
        answers=answers,
        evaluations=evaluations,
        claims=claims,
        questions_asked=questions_asked,
        db=db,
    )

    next_decision_rec = models.InterviewDecision(
        session_id=session.id,
        turn=len(questions_asked) + 1,
        decision=decision_res.decision,
        reason=decision_res.reason,
        inputs=decision_res.inputs,
    )
    db.add(next_decision_rec)
    db.flush()

    if decision_res.decision == "COMPLETE_SESSION":
        session.status = "completed"
        db.commit()
        return {
            "skipped": True,
            "done": True,
            "message": "Interview session completed after skipped question",
            "decision": {
                "decision": decision_res.decision,
                "reason": decision_res.reason,
            }
        }

    q_rec = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=len(questions_asked) + 1,
        question_text=decision_res.question_text,
        question_type=decision_res.question_type,
        source=decision_res.source,
        claim_id=decision_res.claim_id,
        ladder_stage=decision_res.ladder_stage,
        difficulty=decision_res.difficulty,
        time_limit_seconds=decision_res.time_limit_seconds,
        generated_reason=decision_res.reason,
    )
    db.add(q_rec)
    session.current_question_index = len(questions_asked) + 1
    db.commit()
    db.refresh(q_rec)

    return {
        "skipped": True,
        "done": False,
        "question": {
            "id": q_rec.id,
            "question": q_rec.question_text,
            "question_type": q_rec.question_type,
            "source": q_rec.source,
            "ladder_stage": q_rec.ladder_stage,
            "claim_id": q_rec.claim_id,
            "difficulty": q_rec.difficulty,
            "time_limit_seconds": q_rec.time_limit_seconds,
            "sequence_order": q_rec.sequence_order,
            "generated_reason": q_rec.generated_reason,
        },
        "decision": {
            "decision": next_decision_rec.decision,
            "reason": next_decision_rec.reason,
        }
    }


# =========================
# FOLLOW-UP QUESTION
# =========================
@router.post("/followup")
def followup(
    data: FollowUpRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    MAX_FOLLOWUPS = 2

    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == data.session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.followup_count >= MAX_FOLLOWUPS:
        return {"message": "followup_limit_reached", "followup_question": None}

    followup_question = generate_followup(data.question, data.answer)

    record = models.FollowUpQuestion(
        session_id=data.session_id,
        parent_question_id=data.question_id,
        followup_text=followup_question
    )

    db.add(record)
    session.followup_count += 1
    db.commit()

    return {
        "followup_question": followup_question,
        "followup_count": session.followup_count
    }


# =========================
# NEXT ADAPTIVE QUESTION & PROBE LADDER
# =========================
@router.post("/{session_id}/next")
def get_next_question(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates pure deterministic policy to decide the next interview step:
    advancing a claim-probe ladder (T1->T2->T3->T4), probing a new claim,
    triggering a challenge scenario, presenting an adjusted bank question,
    or completing the session.
    Logs every decision in interview_decisions table.
    """
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id,
        models.InterviewSession.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    answers = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == session_id
    ).order_by(models.InterviewAnswer.id.asc()).all()

    evaluations = []
    for a in answers:
        ev = db.query(models.AnswerEvaluation).filter(
            models.AnswerEvaluation.answer_id == a.id
        ).first()
        if ev:
            evaluations.append(ev)

    claims = []
    if session.resume_id:
        claims = db.query(models.ResumeClaim).filter(
            models.ResumeClaim.resume_id == session.resume_id
        ).order_by(models.ResumeClaim.probe_priority.desc()).all()

    questions_asked = db.query(models.InterviewQuestion).filter(
        models.InterviewQuestion.session_id == session_id
    ).order_by(models.InterviewQuestion.sequence_order.asc()).all()

    decision_res = decide_next_question(
        session=session,
        answers=answers,
        evaluations=evaluations,
        claims=claims,
        questions_asked=questions_asked,
        db=db,
    )

    decision_record = models.InterviewDecision(
        session_id=session.id,
        turn=len(questions_asked) + 1,
        decision=decision_res.decision,
        reason=decision_res.reason,
        inputs=decision_res.inputs,
    )
    db.add(decision_record)
    db.flush()

    if decision_res.decision == "COMPLETE_SESSION":
        session.status = "completed"
        db.commit()
        return {
            "done": True,
            "message": "Interview session completed",
            "decision": {
                "decision": decision_res.decision,
                "reason": decision_res.reason,
            }
        }

    q_rec = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=len(questions_asked) + 1,
        question_text=decision_res.question_text,
        question_type=decision_res.question_type,
        source=decision_res.source,
        claim_id=decision_res.claim_id,
        ladder_stage=decision_res.ladder_stage,
        difficulty=decision_res.difficulty,
        time_limit_seconds=decision_res.time_limit_seconds,
        generated_reason=decision_res.reason,
    )
    db.add(q_rec)
    session.current_question_index = len(questions_asked) + 1
    db.commit()
    db.refresh(q_rec)

    caption = None
    if decision_res.claim_id:
        claim_obj = db.query(models.ResumeClaim).filter(models.ResumeClaim.id == decision_res.claim_id).first()
        if claim_obj:
            project_title = None
            if claim_obj.project_id:
                proj = db.query(models.ResumeProject).filter(models.ResumeProject.id == claim_obj.project_id).first()
                if proj:
                    project_title = proj.title
            tech_list = []
            if claim_obj.technologies:
                try:
                    tech_list = json.loads(claim_obj.technologies) if isinstance(claim_obj.technologies, str) else claim_obj.technologies
                except Exception:
                    pass
            tech_str = tech_list[0] if tech_list else None
            anchor = project_title or tech_str or "Resume Claim"
            caption = f"Follow-up on: {anchor}"
    elif decision_res.source in ("pressure_trigger", "challenge") or decision_res.question_type == "challenge":
        caption = "Technical Challenge Scenario"

    return {
        "done": False,
        "question": {
            "id": q_rec.id,
            "question": q_rec.question_text,
            "question_type": q_rec.question_type,
            "source": q_rec.source,
            "ladder_stage": q_rec.ladder_stage,
            "claim_id": q_rec.claim_id,
            "caption": caption,
            "difficulty": q_rec.difficulty,
            "time_limit_seconds": q_rec.time_limit_seconds,
            "sequence_order": q_rec.sequence_order,
            "generated_reason": q_rec.generated_reason,
        },
        "decision": {
            "decision": decision_record.decision,
            "reason": decision_record.reason,
        }
    }



# =========================
# COMPLETE INTERVIEW & COMPUTE SESSION SCORE
# =========================
@router.post("/{session_id}/complete")
def complete_interview(
    session_id: int,
    data: Optional[CompleteInterviewRequest] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data is None:
        data = CompleteInterviewRequest()
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    existing_score = db.query(models.SessionScore).filter(
        models.SessionScore.session_id == session_id
    ).first()

    if session.status == "completed" and existing_score:
        return {
            "session_id": session.id,
            "status": "completed",
            "readiness_score": existing_score.readiness_score or existing_score.behavioral_score,
            "delivery_measured": existing_score.behavioral_score is not None,
            "weights_used": json.loads(existing_score.weights_used or "{}"),
            "consistency_source": existing_score.consistency_source or "session_level",
            "subscores": {
                "communication": existing_score.communication_score,
                "technical": existing_score.technical_score,
                "delivery": existing_score.behavioral_score,
                "resume_consistency": existing_score.resume_consistency_score,
            },
            "strongest_category": existing_score.strongest_category,
            "weakest_category": existing_score.weakest_category,
            "insights": json.loads(existing_score.insights or "[]")
        }
    eye_percent = data.eye_contact_percent
    blink_rate = data.blink_rate
    pause_rate = data.pause_rate if data.pause_rate is not None else 2.0

    behavioral_record = models.BehavioralMetrics(
        session_id=session.id,
        eye_contact_percent=eye_percent,
        blink_rate=blink_rate,
        pause_rate=pause_rate
    )
    db.add(behavioral_record)

    # Calculate delivery score (returns None if visual sensors are null/unmeasured)
    calculated_deliv_score = calculate_delivery_score(eye_percent, blink_rate, pause_rate)

    # Fetch answers to compute evidence coverage and filter out skipped/empty turns
    answers = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == session.id
    ).all()

    meaningful_answers = []
    skipped_count = 0
    empty_count = 0

    for a in answers:
        transcript = (a.transcript or "").strip()
        if transcript.startswith("[SKIPPED]"):
            skipped_count += 1
        elif len(transcript.split()) < 3:
            empty_count += 1
        else:
            meaningful_answers.append(a)

    total_turns = len(answers)
    evidence_coverage = round((len(meaningful_answers) / total_turns) * 100, 1) if total_turns > 0 else 0.0

    # Fetch answer evaluations for meaningful answers only
    meaningful_answer_ids = {a.id for a in meaningful_answers}
    evaluations = db.query(models.AnswerEvaluation).filter(
        models.AnswerEvaluation.answer_id.in_(meaningful_answer_ids)
    ).all() if meaningful_answer_ids else []

    overall_scores = [e.overall_score for e in evaluations if e.overall_score is not None]
    tech_scores = [e.technical_score for e in evaluations if e.technical_score is not None]
    comm_scores = [e.structure_score for e in evaluations if e.structure_score is not None]
    cons_scores = [e.consistency_score for e in evaluations if e.consistency_score is not None]

    # Evaluate per-claim consistency and derive session consistency score if sufficient turns
    claim_consistency_res = evaluate_session_claim_consistency(session_id=session.id, db=db)
    consistency_source = claim_consistency_res["consistency_source"]
    if consistency_source == "claim_level" and claim_consistency_res["derived_score"] is not None and meaningful_answers:
        cons_scores = [claim_consistency_res["derived_score"]]

    # When zero meaningful answers were submitted, delivery sensor data cannot create a high readiness score
    if not meaningful_answers:
        calculated_deliv_score = None

    session_score_data = calculate_session_score(
        answer_scores=overall_scores,
        delivery_score=calculated_deliv_score,
        technical_scores=tech_scores,
        communication_scores=comm_scores,
        consistency_scores=cons_scores,
        evidence_coverage=evidence_coverage
    )

    # Persist session score with weights_used and consistency_source
    score_record = models.SessionScore(
        session_id=session.id,
        behavioral_score=session_score_data["delivery_score"],
        communication_score=session_score_data["communication_score"],
        technical_score=session_score_data["technical_score"],
        resume_consistency_score=session_score_data["resume_consistency_score"],
        consistency_source=consistency_source,
        readiness_score=session_score_data["final_readiness_score"],
        weights_used=json.dumps(session_score_data["weights_used"]),
        strongest_category=session_score_data["strongest_category"],
        weakest_category=session_score_data["weakest_category"],
        insights=json.dumps(session_score_data["insights"])
    )

    session.status = "completed"
    db.add(score_record)
    db.commit()
    db.refresh(score_record)

    return {
        "session_id": session.id,
        "status": "completed",
        "readiness_score": session_score_data["final_readiness_score"],
        "delivery_measured": session_score_data["delivery_measured"],
        "weights_used": session_score_data["weights_used"],
        "consistency_source": consistency_source,
        "claim_consistency": claim_consistency_res["claim_records"],
        "score_confidence": session_score_data.get("score_confidence", "High"),
        "confidence_explanation": session_score_data.get("confidence_explanation", ""),
        "subscores": {
            "communication": session_score_data["communication_score"],
            "technical": session_score_data["technical_score"],
            "delivery": session_score_data["delivery_score"],
            "delivery_measured": session_score_data["delivery_measured"],
            "behavioral": session_score_data["behavioral_score"],
            "resume_consistency": session_score_data["resume_consistency_score"],
            "consistency_source": consistency_source
        },
        "strongest_category": session_score_data["strongest_category"],
        "weakest_category": session_score_data["weakest_category"],
        "insights": session_score_data["insights"]
    }



# =========================
# SUBMIT BEHAVIORAL (BACKWARD COMPATIBLE)
# =========================
@router.post("/submit")
def submit_interview_legacy(
    data: BehavioralInput,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == data.session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    behavioral = models.BehavioralMetrics(
        session_id=session.id,
        eye_contact_percent=data.eye_contact_percent,
        blink_rate=data.blink_rate,
        pause_rate=data.pause_rate
    )
    db.add(behavioral)

    beh_score = calculate_behavioral_score(
        data.eye_contact_percent,
        data.blink_rate,
        data.pause_rate
    )

    answers = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == session.id
    ).all()

    meaningful_answers = [
        a for a in answers
        if not (a.transcript or "").strip().startswith("[SKIPPED]") and len((a.transcript or "").strip().split()) >= 3
    ]
    total_turns = len(answers)
    evidence_coverage = round((len(meaningful_answers) / total_turns) * 100, 1) if total_turns > 0 else 0.0

    meaningful_answer_ids = {a.id for a in meaningful_answers}
    evaluations = db.query(models.AnswerEvaluation).filter(
        models.AnswerEvaluation.answer_id.in_(meaningful_answer_ids)
    ).all() if meaningful_answer_ids else []

    overall_scores = [e.overall_score for e in evaluations if e.overall_score is not None]
    tech_scores = [e.technical_score for e in evaluations if e.technical_score is not None]
    comm_scores = [e.structure_score for e in evaluations if e.structure_score is not None]

    if not meaningful_answers:
        beh_score = None

    score_data = calculate_session_score(
        answer_scores=overall_scores,
        behavioral_score=beh_score,
        technical_scores=tech_scores,
        communication_scores=comm_scores,
        evidence_coverage=evidence_coverage
    )

    score = models.SessionScore(
        session_id=session.id,
        behavioral_score=score_data["behavioral_score"],
        communication_score=score_data["communication_score"],
        technical_score=score_data["technical_score"],
        resume_consistency_score=score_data["resume_consistency_score"],
        readiness_score=score_data["final_readiness_score"],
        strongest_category=score_data["strongest_category"],
        weakest_category=score_data["weakest_category"],
        insights=json.dumps(score_data["insights"])
    )

    session.status = "completed"
    db.add(score)
    db.commit()

    return {
        "session_id": session.id,
        "behavioral_score": beh_score,
        "readiness_score": score_data["final_readiness_score"]
    }


# =========================
# GET RESULT (BACKWARD COMPATIBLE)
# =========================
@router.get("/result/{session_id}")
def get_result(
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

    score = db.query(models.SessionScore).filter(
        models.SessionScore.session_id == session_id
    ).first()

    evaluations = db.query(models.AnswerEvaluation).join(
        models.InterviewAnswer
    ).filter(
        models.InterviewAnswer.session_id == session_id
    ).all()

    answer_scores = [e.overall_score for e in evaluations]

    if score:
        return {
            "session_id": session_id,
            "answer_scores": answer_scores,
            "behavioral_score": score.behavioral_score,
            "final_score": score.readiness_score
        }

    return {
        "session_id": session_id,
        "answer_scores": answer_scores,
        "behavioral_score": 75.0,
        "final_score": 75.0
    }


# =========================
# DELETE INTERVIEW SESSION
# =========================
@router.delete("/{session_id}")
def delete_session(
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

    db.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.source_session_id == session_id
    ).delete(synchronize_session=False)

    db.delete(session)
    db.commit()
    return {
        "message": "Interview session deleted successfully",
        "session_id": session_id
    }
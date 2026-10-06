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
    CompleteInterviewRequest
)
from backend.services.auth_service import get_current_user
from backend.services.evaluation_engine import evaluate_answer
from backend.services.followup_generator import generate_followup
from backend.services.scoring_engine import calculate_session_score
from backend.services.question_selector import select_questions
from backend.services.voice_service import compute_voice_metrics

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

    session = models.InterviewSession(
        user_id=user.id,
        mode=mode,
        difficulty=difficulty,
        target_role=target_role,
        resume_id=data.resume_id,
        total_questions=number_of_questions,
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

    return {
        "session_id": session.id,
        "mode": mode,
        "difficulty": difficulty,
        "target_role": target_role,
        "total_questions": len(selected_questions),
        "questions": selected_questions
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
        prompt_version=evaluation.get("prompt_version", "v1.0")
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
# COMPLETE INTERVIEW & COMPUTE SESSION SCORE
# =========================
@router.post("/{session_id}/complete")
def complete_interview(
    session_id: int,
    data: CompleteInterviewRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id,
        models.InterviewSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Record behavioral / delivery metrics (nullable if camera off/unmeasured)
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

    # Fetch answer evaluations
    evaluations = db.query(models.AnswerEvaluation).join(
        models.InterviewAnswer
    ).filter(
        models.InterviewAnswer.session_id == session.id
    ).all()

    overall_scores = [e.overall_score for e in evaluations] if evaluations else [75.0]
    tech_scores = [e.technical_score for e in evaluations if e.technical_score is not None]
    comm_scores = [e.structure_score for e in evaluations if e.structure_score is not None]
    cons_scores = [e.consistency_score for e in evaluations if e.consistency_score is not None]

    session_score_data = calculate_session_score(
        answer_scores=overall_scores,
        delivery_score=calculated_deliv_score,
        technical_scores=tech_scores,
        communication_scores=comm_scores,
        consistency_scores=cons_scores
    )

    # Persist session score with weights_used
    score_record = models.SessionScore(
        session_id=session.id,
        behavioral_score=session_score_data["delivery_score"],
        communication_score=session_score_data["communication_score"],
        technical_score=session_score_data["technical_score"],
        resume_consistency_score=session_score_data["resume_consistency_score"],
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
        "subscores": {
            "communication": session_score_data["communication_score"],
            "technical": session_score_data["technical_score"],
            "delivery": session_score_data["delivery_score"],
            "delivery_measured": session_score_data["delivery_measured"],
            "behavioral": session_score_data["behavioral_score"],
            "resume_consistency": session_score_data["resume_consistency_score"]
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

    evaluations = db.query(models.AnswerEvaluation).join(
        models.InterviewAnswer
    ).filter(
        models.InterviewAnswer.session_id == session.id
    ).all()

    overall_scores = [e.overall_score for e in evaluations] if evaluations else [75.0]
    tech_scores = [e.technical_score for e in evaluations if e.technical_score is not None]
    comm_scores = [e.structure_score for e in evaluations if e.structure_score is not None]

    score_data = calculate_session_score(
        answer_scores=overall_scores,
        behavioral_score=beh_score,
        technical_scores=tech_scores,
        communication_scores=comm_scores
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

    db.delete(session)
    db.commit()
    return {
        "message": "Interview session deleted successfully",
        "session_id": session_id
    }
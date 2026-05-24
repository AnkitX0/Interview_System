from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import random

import backend.models as models
from backend.database import get_db
from backend.schemas.schemas import AnswerInput, FollowUpRequest, StartInterviewRequest
from backend.services.evaluation_engine import evaluate_answer
from backend.services.followup_generator import generate_followup
from backend.services.scoring_engine import calculate_session_score

router = APIRouter(prefix="/interview", tags=["Interview"])


# =========================
# START INTERVIEW
# =========================
@router.post("/start")
def start_interview(data: StartInterviewRequest, db: Session = Depends(get_db)):

    mode = data.mode
    difficulty = data.difficulty
    number_of_questions = data.number_of_questions

    session = models.InterviewSession(
        mode=mode,
        difficulty=difficulty,
        total_questions=number_of_questions,
        current_question_index=0,
        followup_count=0,
        status="in_progress"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    query = db.query(models.QuestionBank)

    if difficulty:
        query = query.filter(models.QuestionBank.difficulty == difficulty)

    questions = query.limit(number_of_questions * 3).all()

    if not questions:
        return {"error": "No questions available for selected difficulty"}

    if len(questions) <= number_of_questions:
        selected_questions = questions
    else:
        selected_questions = random.sample(questions, number_of_questions)

    return {
        "session_id": session.id,
        "mode": mode,
        "difficulty": difficulty,
        "total_questions": number_of_questions,
        "questions": [
            {"id": q.id, "question": q.question_text}
            for q in selected_questions
        ]
    }


# =========================
# SUBMIT ANSWER
# =========================
@router.post("/answer")
def submit_answer(data: AnswerInput, db: Session = Depends(get_db)):

    answer = models.InterviewAnswer(
        session_id=data.session_id,
        question_id=data.question_id,
        transcript=data.transcript,
        response_time=data.response_time
    )

    db.add(answer)
    db.commit()
    db.refresh(answer)

    # evaluate answer
    evaluation = evaluate_answer(data.transcript)

    eval_record = models.AnswerEvaluation(
        answer_id=answer.id,
        structure_score=evaluation["structure_score"],
        clarity_score=evaluation["clarity_score"],
        depth_score=evaluation["depth_score"],
        overall_score=evaluation["overall_score"]
    )

    db.add(eval_record)

    # update session progress
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == data.session_id
    ).first()

    if session:
        session.current_question_index += 1
        session.followup_count = 0

    db.commit()

    return {
        "message": "Answer stored and evaluated",
        "score": evaluation["overall_score"]
    }


# =========================
# FOLLOW-UP QUESTION
# =========================
@router.post("/followup")
def followup(data: FollowUpRequest, db: Session = Depends(get_db)):

    MAX_FOLLOWUPS = 2

    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == data.session_id
    ).first()

    if not session:
        return {"error": "Session not found"}

    # stop follow-up loop
    if session.followup_count >= MAX_FOLLOWUPS:
        return {"message": "followup_limit_reached"}

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
# GET RESULT
# =========================
@router.get("/result/{session_id}")
def get_result(session_id: int, db: Session = Depends(get_db)):

    evaluations = db.query(models.AnswerEvaluation).join(
        models.InterviewAnswer
    ).filter(
        models.InterviewAnswer.session_id == session_id
    ).all()

    answer_scores = [e.overall_score for e in evaluations]

    behavioral = db.query(models.BehavioralMetrics).filter(
        models.BehavioralMetrics.session_id == session_id
    ).first()

    behavioral_score = 0

    if behavioral:
        behavioral_score = (
            behavioral.eye_contact_percent * 0.4 +
            (1 - behavioral.blink_rate) * 0.3 +
            (1 - behavioral.pause_rate) * 0.3
        )

    final_score = calculate_session_score(answer_scores, behavioral_score)

    return {
        "session_id": session_id,
        "answer_scores": answer_scores,
        "behavioral_score": behavioral_score,
        "final_score": final_score
    }
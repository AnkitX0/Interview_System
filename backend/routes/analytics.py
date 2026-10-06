import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

import backend.models as models
from backend.database import get_db
from backend.schemas.schemas import ImproveAnswerRequest
from backend.services.answer_improvement_service import improve_interview_answer
from backend.services.scoring_engine import evaluate_rubric_for_answer

router = APIRouter(tags=["Analytics & Reports"])


# =========================
# GET SESSION REPORT
# =========================
@router.get("/report/{session_id}")
def get_session_report(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id
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

        answer_evals.append({
            "answer_id": ans.id,
            "question_id": ans.question_id,
            "question_text": ans.question_text or "Question",
            "transcript": ans.transcript or "",
            "response_time": ans.response_time or 0.0,
            "wpm": ans.wpm or 0.0,
            "filler_count": ans.filler_count or 0,
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
            "suggestions": suggestions
        })

    # Default fallback scores if not completed yet
    readiness = score_record.readiness_score if score_record else 72.0
    comm = score_record.communication_score if score_record else 75.0
    tech = score_record.technical_score if score_record else 70.0
    beh = score_record.behavioral_score if score_record else 75.0
    cons = score_record.resume_consistency_score if score_record else 75.0
    strongest = score_record.strongest_category if score_record else "Communication"
    weakest = score_record.weakest_category if score_record else "Technical"

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
            "Integrate quantifiable outcomes (numbers, scale, percentages) into every behavioral and system response."
        ]

    status_label = "Job-Ready Candidate" if readiness >= 80 else ("Near Interview-Ready" if readiness >= 65 else "Requires Targeted Practice")

    radar_data = [
        {"subject": "Communication", "score": comm, "fullMark": 100},
        {"subject": "Technical Depth", "score": tech, "fullMark": 100},
        {"subject": "Behavioral Signals", "score": beh, "fullMark": 100},
        {"subject": "Resume Consistency", "score": cons, "fullMark": 100}
    ]

    return {
        "session_id": session.id,
        "mode": session.mode,
        "difficulty": session.difficulty,
        "target_role": session.target_role,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "readiness_score": readiness,
        "status_label": status_label,
        "subscores": {
            "communication": comm,
            "technical": tech,
            "behavioral": beh,
            "resume_consistency": cons
        },
        "insights": {
            "strongest_category": strongest,
            "weakest_category": weakest,
            "top_improvements": insights
        },
        "behavioral_metrics": {
            "eye_contact_percent": behavioral.eye_contact_percent if behavioral else 75.0,
            "blink_rate": behavioral.blink_rate if behavioral else 18.0,
            "pause_rate": behavioral.pause_rate if behavioral else 2.0
        },
        "radar_data": radar_data,
        "answers": answer_evals
    }


# =========================
# GET PROGRESS HISTORY
# =========================
@router.get("/progress")
def get_progress_data(db: Session = Depends(get_db)):
    sessions = db.query(models.InterviewSession).order_by(
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

    return {
        "total_interviews": len(sessions),
        "average_readiness_score": avg_score,
        "best_score": best_score,
        "latest_score": latest_score,
        "improvement_percentage": improvement,
        "weakest_category": "Technical Depth",
        "sessions": list(reversed(session_list)),
        "trend": trend_data
    }


# =========================
# FIX MY ANSWER ENDPOINTS
# =========================
@router.post("/answer/{answer_id}/improve")
def improve_answer_by_id(answer_id: int, db: Session = Depends(get_db)):
    answer_rec = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.id == answer_id
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
def improve_custom_answer(data: ImproveAnswerRequest):
    if not data.answer.strip():
        raise HTTPException(status_code=400, detail="Answer text cannot be empty")

    improved_data = improve_interview_answer(
        question=data.question,
        original_answer=data.answer,
        target_role=data.target_role or "Software Engineer"
    )

    return improved_data


"""
backend/services/interview_memory_service.py
Structured Interview Memory Engine.
Builds and maintains candidate session memory across turns.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
from sqlalchemy.orm import Session
import backend.models as models

@dataclass
class InterviewMemory:
    session_id: int
    target_role: str
    mode: str
    difficulty: str
    total_budget: int
    resume_claims: List[Dict[str, Any]] = field(default_factory=list)
    topics_covered: List[str] = field(default_factory=list)
    questions_asked: List[Dict[str, Any]] = field(default_factory=list)
    answers_given: List[Dict[str, Any]] = field(default_factory=list)
    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_points: List[Dict[str, Any]] = field(default_factory=list)
    weak_areas: List[str] = field(default_factory=list)
    strong_areas: List[str] = field(default_factory=list)
    evasion_history: List[Dict[str, Any]] = field(default_factory=list)
    current_depth_level: int = 1

def build_interview_memory(session_id: int, db: Session) -> InterviewMemory:
    """
    Constructs a comprehensive, bounded InterviewMemory snapshot for a session
    by aggregating resume claims, turns, answer evaluations, and evasion history.
    """
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        return InterviewMemory(
            session_id=session_id,
            target_role="Software Engineer",
            mode="technical",
            difficulty="medium",
            total_budget=5
        )

    # 1. Load Resume Claims if available
    claims_data = []
    if session.resume_id:
        claims = db.query(models.ResumeClaim).filter(
            models.ResumeClaim.resume_id == session.resume_id
        ).order_by(models.ResumeClaim.probe_priority.desc()).all()
        for c in claims:
            claims_data.append({
                "id": c.id,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "has_metric": c.has_metric,
                "probe_priority": c.probe_priority or 0.5,
                "verified": False,
            })

    # 2. Load Questions & Answers
    questions = db.query(models.InterviewQuestion).filter(
        models.InterviewQuestion.session_id == session_id
    ).order_by(models.InterviewQuestion.sequence_order.asc()).all()

    answers = db.query(models.InterviewAnswer).filter(
        models.InterviewAnswer.session_id == session_id
    ).order_by(models.InterviewAnswer.id.asc()).all()

    questions_asked = []
    for q in questions:
        questions_asked.append({
            "id": q.id,
            "sequence_order": q.sequence_order,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "source": q.source,
            "claim_id": q.claim_id,
            "ladder_stage": q.ladder_stage,
            "difficulty": q.difficulty,
        })

    answers_given = []
    evaluations_list = []
    unresolved_points = []
    weak_areas = []
    strong_areas = []
    evasion_history = []
    topics_covered = []

    for idx, ans in enumerate(answers):
        answers_given.append({
            "id": ans.id,
            "question_id": ans.question_id,
            "question_text": ans.question_text,
            "transcript": ans.transcript,
            "duration_seconds": ans.duration_seconds,
            "wpm": ans.wpm,
            "filler_count": ans.filler_count,
        })

        ev = db.query(models.AnswerEvaluation).filter(
            models.AnswerEvaluation.answer_id == ans.id
        ).first()

        if ev:
            ev_dict = {
                "overall_score": ev.overall_score,
                "technical_score": ev.technical_score,
                "reasoning_score": ev.reasoning_score,
                "structure_score": ev.structure_score,
                "consistency_score": ev.consistency_score,
                "directness_score": getattr(ev, "directness_score", 80.0) or 80.0,
                "candidate_diversion": getattr(ev, "candidate_diversion", False) or False,
                "unresolved_point": getattr(ev, "unresolved_point", None),
                "strengths": json.loads(ev.strengths or "[]"),
                "weaknesses": json.loads(ev.weaknesses or "[]"),
                "missing_concepts": json.loads(ev.missing_concepts or "[]"),
            }
            evaluations_list.append(ev_dict)

            # Categorize strengths, weaknesses, and evasions
            if ev_dict["technical_score"] < 60.0:
                weak_areas.append(f"Turn {idx + 1}: {ans.question_text[:40]}")
            elif ev_dict["technical_score"] >= 80.0:
                strong_areas.append(f"Turn {idx + 1}: {ans.question_text[:40]}")

            if ev_dict["candidate_diversion"] or ev_dict["directness_score"] < 50.0 or ev_dict["unresolved_point"]:
                point_desc = ev_dict["unresolved_point"] or f"Specific evidence for question '{ans.question_text[:50]}'"
                unresolved_points.append({
                    "turn": idx + 1,
                    "question_text": ans.question_text,
                    "candidate_transcript": ans.transcript,
                    "unresolved_point": point_desc,
                })
                evasion_history.append({
                    "turn": idx + 1,
                    "question": ans.question_text,
                    "evasion_evidence": ev_dict["unresolved_point"] or "Answer diverged from core question prompt.",
                })

            if ans.question_text:
                topics_covered.append(ans.question_text[:30])

    # Calculate current depth level based on turns and score progression
    depth_level = min(8, max(1, len(answers) + 1))

    return InterviewMemory(
        session_id=session_id,
        target_role=session.target_role or "Software Engineer",
        mode=session.mode or "technical",
        difficulty=session.difficulty or "medium",
        total_budget=session.total_questions or 5,
        resume_claims=claims_data,
        topics_covered=topics_covered,
        questions_asked=questions_asked,
        answers_given=answers_given,
        evaluations=evaluations_list,
        unresolved_points=unresolved_points,
        weak_areas=weak_areas,
        strong_areas=strong_areas,
        evasion_history=evasion_history,
        current_depth_level=depth_level,
    )

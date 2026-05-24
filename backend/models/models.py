from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from backend.database import Base


# -------------------------
# Interview Session
# -------------------------
class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)

    mode = Column(String)
    difficulty = Column(String)

    total_questions = Column(Integer)

    current_question_index = Column(Integer, default=0)
    followup_count = Column(Integer, default=0)

    status = Column(String, default="in_progress")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# -------------------------
# Question Bank
# -------------------------
class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)

    question_text = Column(Text, nullable=False)

    category = Column(String)   # HR / Technical / Behavioral
    difficulty = Column(String) # easy / medium / hard

    role = Column(String)       # optional (ai, backend, frontend)


# -------------------------
# Interview Answers
# -------------------------
class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    question_id = Column(Integer)

    transcript = Column(Text)

    response_time = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# -------------------------
# Answer Evaluation
# -------------------------
class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True)

    answer_id = Column(Integer, ForeignKey("interview_answers.id"))

    structure_score = Column(Float)
    clarity_score = Column(Float)
    depth_score = Column(Float)

    overall_score = Column(Float)


# -------------------------
# Follow-up Questions
# -------------------------
class FollowUpQuestion(Base):
    __tablename__ = "followup_questions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("interview_sessions.id"))

    parent_question_id = Column(Integer)

    followup_text = Column(Text)


# -------------------------
# Behavioral Metrics
# -------------------------
class BehavioralMetrics(Base):
    __tablename__ = "behavioral_metrics"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("interview_sessions.id"))

    eye_contact_percent = Column(Float)
    blink_rate = Column(Float)
    pause_rate = Column(Float)


# -------------------------
# Final Session Score
# -------------------------
class SessionScore(Base):
    __tablename__ = "session_scores"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("interview_sessions.id"))

    behavioral_score = Column(Float)
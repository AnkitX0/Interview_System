from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from backend.database import Base


# -------------------------
# Candidate Resume
# -------------------------
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    candidate_name = Column(String, default="Candidate")
    raw_text = Column(Text)
    skills = Column(Text)              # JSON string of list
    experience = Column(Text)          # JSON string or text summary
    education = Column(Text)           # JSON string or text summary
    resume_score = Column(Float, default=75.0)
    strengths = Column(Text)           # JSON string of list
    weak_areas = Column(Text)          # JSON string of list
    suggested_improvements = Column(Text) # JSON string of list
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# -------------------------
# Interview Session
# -------------------------
class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)

    mode = Column(String)
    difficulty = Column(String)
    target_role = Column(String, default="Software Engineer")

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
    category = Column(String)   # HR / Technical / Behavioral / Pressure
    difficulty = Column(String) # easy / medium / hard
    role = Column(String)       # general, backend, frontend, ai


# -------------------------
# Interview Answers
# -------------------------
class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    question_id = Column(Integer)
    question_text = Column(Text, nullable=True)

    transcript = Column(Text)
    response_time = Column(Float)
    duration_seconds = Column(Float, default=0.0)
    wpm = Column(Float, default=0.0)
    filler_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# -------------------------
# Answer Evaluation
# -------------------------
class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey("interview_answers.id"))

    structure_score = Column(Float, default=70.0)
    clarity_score = Column(Float, default=70.0)
    depth_score = Column(Float, default=70.0)
    technical_score = Column(Float, default=70.0)
    reasoning_score = Column(Float, default=70.0)
    star_score = Column(Float, default=70.0)
    consistency_score = Column(Float, default=75.0)

    overall_score = Column(Float, default=70.0)
    strengths = Column(Text, default="[]")
    weaknesses = Column(Text, default="[]")
    missing_concepts = Column(Text, default="[]")
    suggestions = Column(Text, default="[]")


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

    behavioral_score = Column(Float, default=0.0)
    communication_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    resume_consistency_score = Column(Float, default=0.0)
    readiness_score = Column(Float, default=0.0)

    strongest_category = Column(String, default="Communication")
    weakest_category = Column(String, default="Technical")
    insights = Column(Text, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
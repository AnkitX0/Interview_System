from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


# -------------------------
# User Authentication & Profile
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    consents = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profile"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    target_role = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    university = Column(String, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    current_status = Column(String, nullable=True)
    target_companies = Column(JSON, nullable=True)
    interview_goal = Column(String, nullable=True)
    weekly_practice_goal = Column(Integer, nullable=True)

    user = relationship("User", back_populates="profile")


# -------------------------
# Candidate Resume
# -------------------------
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = Column(String)
    candidate_name = Column(String, default="Candidate")
    raw_text = Column(Text)
    skills = Column(Text)              # JSON string of list
    experience = Column(Text)          # JSON string or text summary
    education = Column(Text)           # JSON string or text summary
    resume_score = Column(Float, default=75.0)
    strengths = Column(Text, default="[]")           # JSON string of list
    weak_areas = Column(Text, default="[]")          # JSON string of list
    suggested_improvements = Column(Text, default="[]") # JSON string of list
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="resumes")


# -------------------------
# Interview Session
# -------------------------
class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)

    mode = Column(String)
    difficulty = Column(String)
    target_role = Column(String, default="Software Engineer")

    total_questions = Column(Integer)
    current_question_index = Column(Integer, default=0)
    followup_count = Column(Integer, default=0)

    status = Column(String, default="in_progress")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")
    behavioral_metrics = relationship("BehavioralMetrics", back_populates="session", cascade="all, delete-orphan")
    session_scores = relationship("SessionScore", back_populates="session", cascade="all, delete-orphan")
    followup_questions = relationship("FollowUpQuestion", back_populates="session", cascade="all, delete-orphan")


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
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"))
    question_id = Column(Integer)
    question_text = Column(Text, nullable=True)

    transcript = Column(Text)
    response_time = Column(Float)
    duration_seconds = Column(Float, default=0.0)
    wpm = Column(Float, default=0.0)
    filler_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="answers")
    evaluations = relationship("AnswerEvaluation", back_populates="answer", cascade="all, delete-orphan")
    voice_metrics = relationship("VoiceMetrics", back_populates="answer", uselist=False, cascade="all, delete-orphan")


# -------------------------
# Answer Evaluation
# -------------------------
class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey("interview_answers.id", ondelete="CASCADE"))

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
    engine_used = Column(String, default="rubric")
    prompt_version = Column(String, default="v1.0")

    answer = relationship("InterviewAnswer", back_populates="evaluations")


# -------------------------
# Follow-up Questions
# -------------------------
class FollowUpQuestion(Base):
    __tablename__ = "followup_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"))
    parent_question_id = Column(Integer)
    followup_text = Column(Text)

    session = relationship("InterviewSession", back_populates="followup_questions")


# -------------------------
# Behavioral Metrics (Physical Delivery Signals)
# -------------------------
class BehavioralMetrics(Base):
    __tablename__ = "behavioral_metrics"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"))

    eye_contact_percent = Column(Float, nullable=True)
    blink_rate = Column(Float, nullable=True)
    pause_rate = Column(Float, nullable=True)

    session = relationship("InterviewSession", back_populates="behavioral_metrics")


# -------------------------
# Final Session Score
# -------------------------
class SessionScore(Base):
    __tablename__ = "session_scores"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"))

    behavioral_score = Column(Float, nullable=True, default=None)
    communication_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    resume_consistency_score = Column(Float, default=0.0)
    readiness_score = Column(Float, default=0.0)

    strongest_category = Column(String, default="Communication")
    weakest_category = Column(String, default="Technical")
    insights = Column(Text, default="[]")
    weights_used = Column(Text, default="{}") # JSON storing normalized weights used
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="session_scores")


# -------------------------
# Voice Metrics (Per Answer)
# -------------------------
class VoiceMetrics(Base):
    __tablename__ = "voice_metrics"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    words_per_minute = Column(Float, nullable=True)
    filler_word_count = Column(Integer, nullable=True)
    avg_pause_duration = Column(Float, nullable=True)
    longest_pause = Column(Float, nullable=True)
    pause_count = Column(Integer, nullable=True)
    silence_ratio = Column(Float, nullable=True)
    vocabulary_diversity_score = Column(Float, nullable=True)
    speech_source = Column(String, default="speech", nullable=False)  # speech | typed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("InterviewAnswer", back_populates="voice_metrics")


# -------------------------
# Consent Records
# -------------------------
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String, nullable=False)  # camera | microphone | transcript_storage
    policy_version = Column(String, nullable=False)
    granted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="consents")
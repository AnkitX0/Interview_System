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
    practice_recommendations = relationship("PracticeRecommendation", back_populates="user", cascade="all, delete-orphan")


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
    role_fit_scores = Column(JSON, default=dict)
    risk_areas = Column(JSON, default=list)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="resumes")
    skills_list = relationship("ResumeSkill", back_populates="resume", cascade="all, delete-orphan")
    projects = relationship("ResumeProject", back_populates="resume", cascade="all, delete-orphan")
    claims = relationship("ResumeClaim", back_populates="resume", cascade="all, delete-orphan")
    flags = relationship("ResumeFlag", back_populates="resume", cascade="all, delete-orphan")


# -------------------------
# Resume Intelligence Components
# -------------------------
class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    evidenced = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resume = relationship("Resume", back_populates="skills_list")


class ResumeProject(Base):
    __tablename__ = "resume_projects"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    technologies = Column(JSON, default=list)
    bullets = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resume = relationship("Resume", back_populates="projects")
    claims = relationship("ResumeClaim", back_populates="project", cascade="all, delete-orphan")


class ResumeClaim(Base):
    __tablename__ = "resume_claims"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("resume_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String, nullable=False, default="general")
    technologies = Column(JSON, default=list)
    has_metric = Column(Boolean, default=False)
    probe_priority = Column(Float, default=0.5)
    reasons = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resume = relationship("Resume", back_populates="claims")
    project = relationship("ResumeProject", back_populates="claims")
    flags = relationship("ResumeFlag", back_populates="claim", cascade="all, delete-orphan")


class ResumeFlag(Base):
    __tablename__ = "resume_flags"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id = Column(Integer, ForeignKey("resume_claims.id", ondelete="CASCADE"), nullable=True, index=True)
    flag_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False, default="info")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resume = relationship("Resume", back_populates="flags")
    claim = relationship("ResumeClaim", back_populates="flags")


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
    questions_list = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    decisions = relationship("InterviewDecision", back_populates="session", cascade="all, delete-orphan")
    claim_consistencies = relationship("ClaimConsistency", back_populates="session", cascade="all, delete-orphan")


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
    visual_metrics = relationship("AnswerVisualMetrics", back_populates="answer", uselist=False, cascade="all, delete-orphan")


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

    # Verification risk evaluation
    verification_risk_score = Column(Float, nullable=True)
    verification_risk_level = Column(String, nullable=True)
    verification_risk_evidence = Column(JSON, default=list)
    verification_risk_explanation = Column(Text, nullable=True)

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
# Adaptive Interview Questions & Probes
# -------------------------
class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_order = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False, default="bank")  # bank | probe | followup | challenge
    source = Column(String, nullable=False, default="bank")  # bank | resume_claim | followup | pressure_trigger
    claim_id = Column(Integer, ForeignKey("resume_claims.id", ondelete="SET NULL"), nullable=True, index=True)
    ladder_stage = Column(String, nullable=True)  # T1_FOUNDATION | T2_TRADE_OFFS | T3_INCIDENT | T4_EDGE_CASE
    difficulty = Column(String, default="medium")
    time_limit_seconds = Column(Integer, nullable=True)
    generated_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="questions_list")


class InterviewDecision(Base):
    __tablename__ = "interview_decisions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)  # PROBE_CLAIM | ADVANCE_LADDER | NEXT_BANK_QUESTION | TRIGGER_CHALLENGE | COMPLETE_SESSION
    reason = Column(Text, nullable=False)
    inputs = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="decisions")


class ClaimConsistency(Base):
    __tablename__ = "claim_consistency"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id = Column(Integer, ForeignKey("resume_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False, default="unverified")  # supported | partially_supported | unsupported | contradicted | unverified
    evidence = Column(JSON, default=list)
    answers_considered = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="claim_consistencies")


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
    consistency_source = Column(String, default="heuristic")
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
# Extended Visual Metrics (Per Answer)
# -------------------------
class AnswerVisualMetrics(Base):
    __tablename__ = "answer_visual_metrics"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    head_alignment_percent = Column(Float, nullable=True)
    blink_rate = Column(Float, nullable=True)
    head_movement_variance = Column(Float, nullable=True)
    face_visibility_ratio = Column(Float, nullable=True)
    head_shift_count = Column(Integer, nullable=True)
    frames_sampled = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("InterviewAnswer", back_populates="visual_metrics")


# -------------------------
# Consent Records
# -------------------------
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String, nullable=False)  # camera | microphone | transcript_storage
    policy_version = Column(String, default="2.0", server_default="2.0", nullable=False)
    granted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="consents")


# -------------------------
# Practice Recommendations (Phase 4)
# -------------------------
class PracticeRecommendation(Base):
    __tablename__ = "practice_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    weakness_type = Column(String, nullable=False)
    dimension = Column(String, nullable=False)
    priority = Column(Integer, default=1)  # 1 = primary, 2 = secondary
    rationale = Column(Text, nullable=False)
    practice_type = Column(String, nullable=False)  # STRUCTURED_ANSWER | TECHNICAL_DEPTH | PROJECT_DEFENSE | etc.
    target_count = Column(Integer, default=5)
    difficulty = Column(String, default="medium")
    status = Column(String, default="pending")  # pending | in_progress | completed | dismissed
    decision_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="practice_recommendations")
    source_session = relationship("InterviewSession")
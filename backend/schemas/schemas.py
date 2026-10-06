from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ---------------------------
# Start Interview Request
# ---------------------------
class StartInterviewRequest(BaseModel):
    mode: str = "practice"
    difficulty: str = "easy"
    number_of_questions: int = 3
    resume_id: Optional[int] = None
    target_role: Optional[str] = "Software Engineer"


# ---------------------------
# Dimension Evidence Contract
# ---------------------------
class DimensionEvaluation(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="0-100 dimension score")
    evidence: List[str] = Field(default_factory=list, description="Concrete signals derived directly from answer text")
    explanation: str = Field(..., description="Observable rationale for the dimension score")
    recommended_action: str = Field(..., description="Actionable recommendation for improvement")


# ---------------------------
# Answer Evaluation Response
# ---------------------------
class AnswerEvaluationResponse(BaseModel):
    message: str = "Answer stored and evaluated successfully"
    answer_id: Optional[int] = None
    score: float
    dimensions: Dict[str, DimensionEvaluation] = Field(default_factory=dict)
    structure: Optional[DimensionEvaluation] = None
    technical: Optional[DimensionEvaluation] = None
    reasoning: Optional[DimensionEvaluation] = None
    star: Optional[DimensionEvaluation] = None
    consistency: Optional[DimensionEvaluation] = None
    engine_used: Optional[str] = "rubric"
    prompt_version: Optional[str] = "v1.0"

    # Backward compatibility fields (Deprecated)
    structure_score: Optional[float] = Field(None, deprecated=True)
    technical_score: Optional[float] = Field(None, deprecated=True)
    reasoning_score: Optional[float] = Field(None, deprecated=True)
    star_score: Optional[float] = Field(None, deprecated=True)
    consistency_score: Optional[float] = Field(None, deprecated=True)
    strengths: Optional[List[str]] = Field(None, deprecated=True)
    weaknesses: Optional[List[str]] = Field(None, deprecated=True)
    missing_concepts: Optional[List[str]] = Field(None, deprecated=True)
    suggestions: Optional[List[str]] = Field(None, deprecated=True)


# ---------------------------
# Submit Answer Input
# ---------------------------
class AnswerInput(BaseModel):
    session_id: int
    question_id: int
    transcript: str
    response_time: Optional[float] = 0.0
    question_text: Optional[str] = ""
    duration_seconds: Optional[float] = 0.0
    wpm: Optional[float] = 0.0
    filler_count: Optional[int] = 0
    speech_segments: Optional[List[Dict[str, float]]] = None
    speech_source: Optional[str] = "speech"


# ---------------------------
# Generate Follow-up Question
# ---------------------------
class FollowUpRequest(BaseModel):
    session_id: int
    question_id: int
    question: str
    answer: str


# ---------------------------
# Submit Behavioral / Delivery Metrics
# ---------------------------
class BehavioralInput(BaseModel):
    session_id: int
    eye_contact_percent: Optional[float] = None
    blink_rate: Optional[float] = None
    pause_rate: Optional[float] = 2.0


# ---------------------------
# Complete Interview Request
# ---------------------------
class CompleteInterviewRequest(BaseModel):
    eye_contact_percent: Optional[float] = None
    blink_rate: Optional[float] = None
    pause_rate: Optional[float] = 2.0
    duration_seconds: Optional[float] = 0.0


# ---------------------------
# Resume Analyze Request
# ---------------------------
class ResumeAnalyzeRequest(BaseModel):
    text: Optional[str] = None
    resume_id: Optional[int] = None


# ---------------------------
# Fix My Answer Request
# ---------------------------
class ImproveAnswerRequest(BaseModel):
    question: str
    answer: str
    target_role: Optional[str] = "Software Engineer"


# ---------------------------
# Authentication & Profile Schemas
# ---------------------------
class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, description="User email address")
    password: str = Field(..., min_length=10, description="Password (at least 10 characters)")
    full_name: Optional[str] = Field(None, description="User full name")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserProfileSchema(BaseModel):
    target_role: Optional[str] = None
    domain: Optional[str] = None
    experience_level: Optional[str] = None
    university: Optional[str] = None
    graduation_year: Optional[int] = None
    current_status: Optional[str] = None
    target_companies: Optional[List[str]] = None
    interview_goal: Optional[str] = None
    weekly_practice_goal: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    profile: Optional[UserProfileSchema] = None


class PasswordConfirmRequest(BaseModel):
    password: str = Field(..., description="Password required for critical account actions")


# ---------------------------
# Speech Segment Schema (Voice Metrics)
# ---------------------------
class SpeechSegment(BaseModel):
    start: float = Field(..., ge=0.0, description="Start timestamp in seconds relative to answer start")
    end: float = Field(..., ge=0.0, description="End timestamp in seconds relative to answer start")


# ---------------------------
# Consent Record Schemas
# ---------------------------
class ConsentInput(BaseModel):
    consent_type: str = Field(..., description="Type of consent: camera | microphone | transcript_storage")
    granted: bool = Field(..., description="True if granted, False if withdrawn")
    policy_version: Optional[str] = Field(None, description="Policy version granted")


class ConsentResponse(BaseModel):
    consent_type: str
    granted: bool
    policy_version: str
    updated_at: Optional[Any] = None
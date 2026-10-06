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


# ---------------------------
# Generate Follow-up Question
# ---------------------------
class FollowUpRequest(BaseModel):
    session_id: int
    question_id: int
    question: str
    answer: str


# ---------------------------
# Submit Behavioral Metrics
# ---------------------------
class BehavioralInput(BaseModel):
    session_id: int
    eye_contact_percent: float = 75.0
    blink_rate: float = 18.0
    pause_rate: float = 2.0


# ---------------------------
# Complete Interview Request
# ---------------------------
class CompleteInterviewRequest(BaseModel):
    eye_contact_percent: Optional[float] = 75.0
    blink_rate: Optional[float] = 18.0
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
from pydantic import BaseModel
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
# Submit Answer
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
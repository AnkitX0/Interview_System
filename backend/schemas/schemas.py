from pydantic import BaseModel


# ---------------------------
# Start Interview Request
# ---------------------------
class StartInterviewRequest(BaseModel):
    mode: str
    difficulty: str
    number_of_questions: int


# ---------------------------
# Submit Answer
# ---------------------------
class AnswerInput(BaseModel):
    session_id: int
    question_id: int
    transcript: str
    response_time: float


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
    eye_contact_percent: float
    blink_rate: float
    pause_rate: float
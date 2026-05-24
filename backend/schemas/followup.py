from pydantic import BaseModel

class FollowUpRequest(BaseModel):
    session_id: int
    question_id: int
    question: str
    answer: str
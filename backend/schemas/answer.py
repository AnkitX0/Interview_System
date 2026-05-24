from pydantic import BaseModel


class AnswerInput(BaseModel):
    session_id: int
    question_id: int
    transcript: str
    response_time: int
from pydantic import BaseModel

class StartInterviewRequest(BaseModel):
    mode: str
    difficulty: str
    number_of_questions: int
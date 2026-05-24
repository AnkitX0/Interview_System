from sqlalchemy import Column, Integer, Text, ForeignKey
from backend.database import Base


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    question_id = Column(Integer)

    transcript = Column(Text)

    response_time = Column(Integer)
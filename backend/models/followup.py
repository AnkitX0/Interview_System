
from sqlalchemy import Column, Integer, Text, ForeignKey
from backend.database import Base

class FollowUpQuestion(Base):
    __tablename__ = "followup_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    parent_question_id = Column(Integer)
    followup_text = Column(Text)
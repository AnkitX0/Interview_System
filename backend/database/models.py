from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from datetime import datetime
from .connection import Base

class InterviewQuestion(Base):

    __tablename__ = "interview_question_bank"

    id = Column(Integer, primary_key=True, index=True)

    question_text = Column(String, nullable=False)

    question_category = Column(String)
    question_type = Column(String)

    difficulty_level = Column(String)

    role_target = Column(String)
    domain = Column(String)

    expected_keywords = Column(JSON)

    evaluation_rubric = Column(JSON)

    followup_possible = Column(Boolean)

    created_at = Column(DateTime, default=datetime.utcnow)
from sqlalchemy import Column, Integer, Float, ForeignKey
from backend.database import Base


class AnswerEvaluation(Base):

    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True)

    answer_id = Column(Integer, ForeignKey("interview_answers.id"))

    structure_score = Column(Float)
    clarity_score = Column(Float)
    depth_score = Column(Float)

    overall_score = Column(Float)
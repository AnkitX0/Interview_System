# from sqlalchemy import Column, Integer, String, Text
# from backend.database import Base


# class QuestionBank(Base):
#     __tablename__ = "question_bank"

#     id = Column(Integer, primary_key=True, index=True)

#     question_text = Column(Text, nullable=False)

#     category = Column(String, nullable=False)     
#     # HR, Behavioral, Technical, Resume, Pressure

#     difficulty = Column(String, nullable=False)   
#     # easy, medium, hard

#     role = Column(String, nullable=True)          
#     # backend, ai, frontend, general
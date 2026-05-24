import random
from sqlalchemy.orm import Session
from backend.models.question import QuestionBank


def select_questions(db, mode, difficulty, count):

    query = db.query(QuestionBank)

    if difficulty:
        query = query.filter(QuestionBank.difficulty == difficulty)

    if mode == "technical":
        query = query.filter(QuestionBank.category == "Technical")

    elif mode == "hr":
        query = query.filter(QuestionBank.category == "HR")

    elif mode == "practice":
        pass  # mixed

    questions = query.all()

    if len(questions) < count:
        return questions

    return random.sample(questions, count)
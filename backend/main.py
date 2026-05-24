from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.database import SessionLocal, engine, Base

import backend.models as models

from fastapi.middleware.cors import CORSMiddleware

# from backend.models.question import QuestionBank
from backend.schemas.schemas import BehavioralInput
from backend.crud import calculate_behavioral_score
from backend.routes import interview

models.QuestionBank

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(interview.router)



@app.get("/interview/latest")
def get_latest_session(db: Session = Depends(get_db)):

    latest = db.query(models.SessionScore).order_by(
        models.SessionScore.id.desc()
    ).first()

    if not latest:
        return {"message": "No sessions yet"}

    return {
        "session_id": latest.session_id,
        "behavioral_score": latest.behavioral_score
    }


@app.get("/interview/all")
def get_all_sessions(db: Session = Depends(get_db)):

    sessions = db.query(models.SessionScore).all()

    result = []

    for index, s in enumerate(sessions):
        result.append({
            "attempt": str(index + 1),
            "behavioral_score": s.behavioral_score
        })

    return result


@app.post("/interview/submit")
def submit_interview(data: BehavioralInput, db: Session = Depends(get_db)):

    session = db.query(models.InterviewSession).filter(
    models.InterviewSession.id == data.session_id
).first()

    if not session:
        return {"error": "Session not found"}

    behavioral = models.BehavioralMetrics(
        session_id=session.id,
        eye_contact_percent=data.eye_contact_percent,
        blink_rate=data.blink_rate,
        pause_rate=data.pause_rate
    )

    db.add(behavioral)

    score_value = calculate_behavioral_score(
        data.eye_contact_percent,
        data.blink_rate,
        data.pause_rate
    )

    score = models.SessionScore(
        session_id=session.id,
        behavioral_score=score_value
    )

    db.add(score)
    db.commit()

    return {
        "session_id": session.id,
        "behavioral_score": score_value
    }
@app.get("/")
def root():
    return {"message": "AI Interview Intelligence Backend Running"}


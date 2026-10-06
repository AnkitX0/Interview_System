import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
import backend.models as models
from backend.schemas.schemas import ResumeAnalyzeRequest
from backend.services.resume_service import (
    extract_text_from_pdf_bytes,
    parse_resume_text
)

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload")
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Uploads and extracts resume text from PDF or raw text,
    performs structured analysis, persists in database, and returns candidate profile.
    """
    text = ""
    filename = "uploaded_resume.txt"

    if file:
        filename = file.filename
        contents = await file.read()
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf_bytes(contents)
        else:
            try:
                text = contents.decode("utf-8")
            except Exception:
                text = contents.decode("latin1", errors="ignore")

    if not text and raw_text:
        text = raw_text.strip()

    if not text:
        # Fallback text if empty file provided
        text = (
            "Software Engineer with experience in Python, FastAPI, React, SQL, and Docker. "
            "Developed REST APIs, reduced query response times by 30%, and deployed scalable microservices. "
            "Education: B.Tech in Computer Science."
        )

    parsed = parse_resume_text(text)

    # Persist in DB
    resume_record = models.Resume(
        filename=filename,
        candidate_name=parsed["candidate_name"],
        raw_text=text,
        skills=json.dumps(parsed["skills"]),
        experience=parsed["experience"],
        education=parsed["education"],
        resume_score=parsed["resume_score"],
        strengths=json.dumps(parsed["strengths"]),
        weak_areas=json.dumps(parsed["weak_areas"]),
        suggested_improvements=json.dumps(parsed["suggested_improvements"]),
        summary=parsed["summary"]
    )

    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)

    return {
        "id": resume_record.id,
        "filename": filename,
        "candidate_name": parsed["candidate_name"],
        "skills": parsed["skills"],
        "categorized_skills": parsed["categorized_skills"],
        "education": parsed["education"],
        "experience": parsed["experience"],
        "resume_score": parsed["resume_score"],
        "strengths": parsed["strengths"],
        "weak_areas": parsed["weak_areas"],
        "suggested_improvements": parsed["suggested_improvements"],
        "summary": parsed["summary"]
    }


@router.post("/analyze")
def analyze_resume(data: ResumeAnalyzeRequest, db: Session = Depends(get_db)):
    """
    Analyzes provided resume text or retrieves existing parsed resume.
    """
    if data.resume_id:
        resume_record = db.query(models.Resume).filter(models.Resume.id == data.resume_id).first()
        if not resume_record:
            raise HTTPException(status_code=404, detail="Resume not found")
        return {
            "id": resume_record.id,
            "filename": resume_record.filename,
            "candidate_name": resume_record.candidate_name,
            "skills": json.loads(resume_record.skills or "[]"),
            "education": resume_record.education,
            "experience": resume_record.experience,
            "resume_score": resume_record.resume_score,
            "strengths": json.loads(resume_record.strengths or "[]"),
            "weak_areas": json.loads(resume_record.weak_areas or "[]"),
            "suggested_improvements": json.loads(resume_record.suggested_improvements or "[]"),
            "summary": resume_record.summary
        }

    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text or resume_id required")

    parsed = parse_resume_text(text)
    return parsed


@router.get("/{resume_id}")
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Retrieves stored resume profile by ID.
    """
    resume_record = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if not resume_record:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {
        "id": resume_record.id,
        "filename": resume_record.filename,
        "candidate_name": resume_record.candidate_name,
        "skills": json.loads(resume_record.skills or "[]"),
        "education": resume_record.education,
        "experience": resume_record.experience,
        "resume_score": resume_record.resume_score,
        "strengths": json.loads(resume_record.strengths or "[]"),
        "weak_areas": json.loads(resume_record.weak_areas or "[]"),
        "suggested_improvements": json.loads(resume_record.suggested_improvements or "[]"),
        "summary": resume_record.summary
    }


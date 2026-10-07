import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from backend.database import get_db
import backend.models as models
from backend.schemas.schemas import ResumeAnalyzeRequest
from backend.services.auth_service import get_current_user
from backend.services.resume_service import (
    extract_text_from_pdf_bytes,
    extract_pdf_page_count,
    sanitize_resume_text,
    validate_resume_document,
    parse_resume_text
)

router = APIRouter(prefix="/resume", tags=["Resume"])


def _persist_parsed_resume_entities(db: Session, resume_record: models.Resume, parsed: Dict[str, Any]):
    """Persists child entities (skills, projects, claims, flags) for a parsed resume."""
    # 1. Clear any existing children
    db.query(models.ResumeFlag).filter(models.ResumeFlag.resume_id == resume_record.id).delete()
    db.query(models.ResumeClaim).filter(models.ResumeClaim.resume_id == resume_record.id).delete()
    db.query(models.ResumeProject).filter(models.ResumeProject.resume_id == resume_record.id).delete()
    db.query(models.ResumeSkill).filter(models.ResumeSkill.resume_id == resume_record.id).delete()
    db.flush()

    # 2. Add ResumeSkill records
    for s_info in parsed.get("skills_detailed", []):
        db.add(models.ResumeSkill(
            resume_id=resume_record.id,
            name=s_info["name"],
            category=s_info["category"],
            confidence=s_info.get("confidence", 1.0),
            evidenced=s_info.get("evidenced", True),
        ))

    # 3. Add ResumeProject records
    project_objs = []
    for p_info in parsed.get("projects", []):
        proj = models.ResumeProject(
            resume_id=resume_record.id,
            title=p_info["title"],
            description=p_info.get("description", ""),
            technologies=p_info.get("technologies", []),
            bullets=p_info.get("bullets", []),
        )
        db.add(proj)
        project_objs.append(proj)
    db.flush()

    # 4. Add ResumeClaim records
    claim_objs = []
    for c_info in parsed.get("claims", []):
        proj_id = None
        p_idx = c_info.get("project_idx")
        if p_idx is not None and 0 <= p_idx < len(project_objs):
            proj_id = project_objs[p_idx].id

        claim = models.ResumeClaim(
            resume_id=resume_record.id,
            project_id=proj_id,
            claim_text=c_info["claim_text"],
            claim_type=c_info["claim_type"],
            technologies=c_info.get("technologies", []),
            has_metric=c_info.get("has_metric", False),
            probe_priority=c_info.get("probe_priority", 0.5),
            reasons=c_info.get("reasons", []),
        )
        db.add(claim)
        claim_objs.append(claim)
    db.flush()

    # 5. Add ResumeFlag records
    for f_info in parsed.get("flags", []):
        c_id = None
        c_idx = f_info.get("claim_idx")
        if c_idx is not None and 0 <= c_idx < len(claim_objs):
            c_id = claim_objs[c_idx].id

        db.add(models.ResumeFlag(
            resume_id=resume_record.id,
            claim_id=c_id,
            flag_type=f_info["flag_type"],
            description=f_info["description"],
            severity=f_info.get("severity", "info"),
        ))

    # 6. Update resume columns
    resume_record.candidate_name = parsed["candidate_name"]
    resume_record.skills = json.dumps(parsed["skills"])
    resume_record.experience = parsed["experience"]
    resume_record.education = parsed["education"]
    resume_record.resume_score = parsed["resume_score"]
    resume_record.strengths = json.dumps(parsed["strengths"])
    resume_record.weak_areas = json.dumps(parsed["weak_areas"])
    resume_record.suggested_improvements = json.dumps(parsed["suggested_improvements"])
    resume_record.summary = parsed["summary"]
    resume_record.role_fit_scores = parsed.get("role_fit_scores", {})
    resume_record.risk_areas = parsed.get("risk_areas", [])


def _build_resume_detail_response(resume: models.Resume, db: Session) -> Dict[str, Any]:
    """Serializes rich resume profile including child skills, projects, claims, and flags."""
    skills_rows = db.query(models.ResumeSkill).filter(models.ResumeSkill.resume_id == resume.id).all()
    projects_rows = db.query(models.ResumeProject).filter(models.ResumeProject.resume_id == resume.id).all()
    claims_rows = db.query(models.ResumeClaim).filter(models.ResumeClaim.resume_id == resume.id).order_by(models.ResumeClaim.probe_priority.desc()).all()
    flags_rows = db.query(models.ResumeFlag).filter(models.ResumeFlag.resume_id == resume.id).all()

    categorized: Dict[str, List[str]] = {}
    for s in skills_rows:
        cat = s.category or "Other Competencies"
        categorized.setdefault(cat, []).append(s.name)

    return {
        "id": resume.id,
        "filename": resume.filename,
        "candidate_name": resume.candidate_name,
        "skills": json.loads(resume.skills or "[]"),
        "categorized_skills": categorized,
        "skills_detailed": [
            {"id": s.id, "name": s.name, "category": s.category, "confidence": s.confidence, "evidenced": s.evidenced}
            for s in skills_rows
        ],
        "projects": [
            {"id": p.id, "title": p.title, "description": p.description, "technologies": p.technologies or [], "bullets": p.bullets or []}
            for p in projects_rows
        ],
        "claims": [
            {
                "id": c.id,
                "project_id": c.project_id,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "technologies": c.technologies or [],
                "has_metric": c.has_metric,
                "probe_priority": c.probe_priority,
                "reasons": c.reasons or []
            }
            for c in claims_rows
        ],
        "flags": [
            {"id": f.id, "claim_id": f.claim_id, "flag_type": f.flag_type, "description": f.description, "severity": f.severity}
            for f in flags_rows
        ],
        "role_fit_scores": resume.role_fit_scores or {},
        "risk_areas": resume.risk_areas or [],
        "education": resume.education,
        "experience": resume.experience,
        "resume_score": resume.resume_score,
        "strengths": json.loads(resume.strengths or "[]"),
        "weak_areas": json.loads(resume.weak_areas or "[]"),
        "suggested_improvements": json.loads(resume.suggested_improvements or "[]"),
        "summary": resume.summary,
        "raw_text": resume.raw_text,
    }


@router.post("/upload")
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads and extracts resume text from PDF or raw text,
    performs structured intelligence analysis, persists in database scoped to user,
    and returns full candidate profile with claims, flags, and role fit.
    """
    text = ""
    filename = "uploaded_resume.txt"
    page_count = None

    if file:
        filename = file.filename
        contents = await file.read()
        if filename.lower().endswith(".pdf"):
            page_count = extract_pdf_page_count(contents)
            text = extract_text_from_pdf_bytes(contents)
        else:
            try:
                text = contents.decode("utf-8")
            except Exception:
                text = contents.decode("latin1", errors="ignore")

    if not text and raw_text:
        text = raw_text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="No document text could be extracted. Please upload a valid PDF or paste resume text."
        )

    clean_text = sanitize_resume_text(text)
    is_valid, error_msg, _details = validate_resume_document(clean_text, filename=filename, page_count=page_count)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    parsed = parse_resume_text(clean_text)

    resume_record = models.Resume(
        user_id=user.id,
        filename=filename,
        raw_text=clean_text,
    )
    db.add(resume_record)
    db.flush()

    _persist_parsed_resume_entities(db, resume_record, parsed)
    db.commit()
    db.refresh(resume_record)

    return _build_resume_detail_response(resume_record, db)


@router.post("/analyze")
def analyze_resume(
    data: ResumeAnalyzeRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes provided resume text or retrieves existing parsed resume scoped to user.
    """
    if data.resume_id:
        resume_record = db.query(models.Resume).filter(
            models.Resume.id == data.resume_id,
            models.Resume.user_id == user.id
        ).first()
        if not resume_record:
            raise HTTPException(status_code=404, detail="Resume not found")
        return _build_resume_detail_response(resume_record, db)

    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text or resume_id required")

    clean_text = sanitize_resume_text(text)
    is_valid, error_msg, _details = validate_resume_document(clean_text)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    parsed = parse_resume_text(clean_text)
    return parsed


@router.get("/{resume_id}")
def get_resume(
    resume_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves stored resume profile by ID scoped to current user.
    """
    resume_record = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if not resume_record:
        raise HTTPException(status_code=404, detail="Resume not found")

    return _build_resume_detail_response(resume_record, db)


@router.post("/{resume_id}/reanalyze")
def reanalyze_resume(
    resume_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Re-runs section parsing, claim extraction, role fit, flags, and probe priorities
    on an existing stored resume owned by current user.
    """
    resume_record = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if not resume_record:
        raise HTTPException(status_code=404, detail="Resume not found")

    parsed = parse_resume_text(resume_record.raw_text or "")
    _persist_parsed_resume_entities(db, resume_record, parsed)
    db.commit()
    db.refresh(resume_record)

    return _build_resume_detail_response(resume_record, db)


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes a resume owned by current user.
    Cascades deletion to all skills, projects, claims, and flags.
    """
    resume_record = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if not resume_record:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.delete(resume_record)
    db.commit()
    return {"message": "Resume deleted successfully", "id": resume_id}

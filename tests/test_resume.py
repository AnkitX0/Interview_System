import pytest
from unittest.mock import patch
import subprocess

from backend.services.resume_service import (
    parse_resume_text,
    extract_text_from_pdf_bytes,
)

SAMPLE_RESUME_TEXT = """
Jane Doe
Email: jane.doe@example.com | Phone: 555-0199 | San Francisco, CA

PROFESSIONAL SUMMARY
Senior Backend Engineer with 5+ years of experience building resilient microservices, 
optimizing databases, and architecting REST APIs.

TECHNICAL SKILLS
Languages: Python, Java, SQL, TypeScript, Bash
Frameworks & Libraries: FastAPI, Django, React, Pandas
Databases: PostgreSQL, Redis, MongoDB
Cloud & DevOps: Docker, Kubernetes, AWS, CI/CD, Git

EXPERIENCE
Senior Software Engineer - CloudTech Solutions (2021 - Present)
- Architected high-throughput REST APIs using FastAPI and PostgreSQL, serving 25,000 requests per second.
- Implemented Redis caching, reducing p99 API query latency by 45%.
- Deployed containerized microservices to AWS EKS with automated CI/CD pipelines.

Software Developer Intern - DevCorp (2019 - 2020)
- Worked on various tasks as assigned and helped the team with bug fixing.

EDUCATION
B.Tech in Computer Science and Engineering, Tech University (2017 - 2021)
GPA: 3.8 / 4.0
"""


def test_resume_text_parsing_structure():
    """Verify skills, education, experience, and candidate name are parsed."""
    profile = parse_resume_text(SAMPLE_RESUME_TEXT)

    assert profile["candidate_name"] == "Jane Doe"
    assert "Python" in profile["skills"]
    assert "Fastapi" in profile["skills"] or "FastAPI" in profile["skills"]
    assert "Postgresql" in profile["skills"] or "PostgreSQL" in profile["skills"]
    assert "Docker" in profile["skills"]
    assert "B.Tech" in profile["education"] or "Computer Science" in profile["education"]
    assert profile["resume_score"] >= 70.0


def test_resume_vague_statement_detection():
    """Verify weak phrasing is flagged."""
    vague_text = """
    Bob Smith
    Developer
    Experience:
    - Worked on various daily tasks as assigned.
    - Responsible for bug fixing and assisted with whatever was needed.
    """
    profile = parse_resume_text(vague_text)
    assert len(profile["weak_areas"]) > 0
    # Score should be penalized for vagueness and lack of metrics
    assert profile["resume_score"] < 75.0


def test_pdf_extraction_fallback_when_pdftotext_missing():
    """Mock absence of system pdftotext; fallback must extract readable text without error."""
    dummy_pdf_bytes = b"%PDF-1.4 ... (Jane Doe Software Engineer) Tj ... ET"

    with patch("subprocess.run", side_effect=FileNotFoundError("pdftotext not found")):
        extracted = extract_text_from_pdf_bytes(dummy_pdf_bytes)
        assert isinstance(extracted, str)
        assert len(extracted) > 0
        assert "Jane Doe" in extracted or "Software Engineer" in extracted


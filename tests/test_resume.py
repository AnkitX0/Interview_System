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


# ===========================================================================
# PHASE 3: RESUME INTELLIGENCE FIXTURE TESTS
# ===========================================================================

def test_fixture_1_strong_quantified_resume():
    """Fixture 1: High-impact quantified metrics, clear architecture, high Backend role fit."""
    text = """
    Marcus Vance
    Email: marcus.vance@example.com
    
    EXPERIENCE
    Staff Infrastructure Engineer - Nexus Corp (2022 - Present)
    - Architected distributed event stream processing using Kafka, Redis, and FastAPI serving 50,000 requests per second.
    - Optimized PostgreSQL query execution plans and indexing, reducing p99 response times by 48%.
    - Scaled Kubernetes cluster infrastructure from 10 to 120 pods while maintaining 99.99% uptime.
    
    SKILLS
    Languages: Python, Go, SQL
    Frameworks: FastAPI, Django
    Databases: PostgreSQL, Redis
    Cloud: Docker, Kubernetes, AWS, Kafka
    
    EDUCATION
    M.S. in Computer Science, State University
    """
    profile = parse_resume_text(text)
    assert profile["candidate_name"] == "Marcus Vance"
    assert len(profile["claims"]) >= 3
    # High probe priority for claims with metrics
    metric_claims = [c for c in profile["claims"] if c["has_metric"]]
    assert len(metric_claims) >= 2
    assert all(c["probe_priority"] >= 0.70 for c in metric_claims)
    # Role fit
    assert profile["role_fit_scores"]["Backend Engineer"] >= 70.0
    assert profile["resume_score"] >= 80.0


def test_fixture_2_vague_resume():
    """Fixture 2: Passive phrasing, zero metrics, high volume of vague_claim flags."""
    text = """
    Alex Walker
    Software Developer
    
    EXPERIENCE
    - Worked on various backend features and daily tasks as assigned.
    - Assisted with database queries and helped the team with maintenance.
    - Responsible for bug fixing and participating in weekly sprint meetings.
    
    SKILLS
    Python, SQL
    """
    profile = parse_resume_text(text)
    assert profile["candidate_name"] == "Alex Walker"
    vague_flags = [f for f in profile["flags"] if f["flag_type"] == "vague_claim"]
    assert len(vague_flags) >= 2
    assert not any(c["has_metric"] for c in profile["claims"])
    assert profile["resume_score"] < 70.0
    assert any("passive" in r.lower() or "ownership" in r.lower() for r in profile["risk_areas"])


def test_fixture_3_ml_heavy_resume():
    """Fixture 3: ML competencies, fine-tuning, high ML Engineer role fit."""
    text = """
    Dr. Elena Rostova
    Machine Learning Specialist
    
    EXPERIENCE
    Senior Research Engineer - DeepAI Labs
    - Fine-tuned transformer models using PyTorch and HuggingFace for real-time document summarization.
    - Trained convolutional neural networks with TensorFlow and deployed on Triton Inference Server.
    - Built feature engineering pipelines using Pandas, NumPy, and Scikit-Learn processing 20M tokens daily.
    
    SKILLS
    Python, PyTorch, TensorFlow, HuggingFace, Transformers, Scikit-Learn, MLOps, NLP
    """
    profile = parse_resume_text(text)
    assert profile["candidate_name"] == "Elena Rostova"
    assert profile["role_fit_scores"]["ML Engineer"] > profile["role_fit_scores"]["Frontend Engineer"]
    assert profile["role_fit_scores"]["ML Engineer"] >= 70.0
    ml_claims = [c for c in profile["claims"] if any(t.lower() in ("pytorch", "tensorflow", "transformers") for t in c["technologies"])]
    assert len(ml_claims) >= 1


def test_fixture_4_unheaded_resume():
    """Fixture 4: Unstructured bullet points without explicit section titles."""
    text = """
    David Kim
    david@example.com
    
    * Built real-time analytics dashboard with React, TypeScript, and FastAPI.
    * Engineered distributed cache layer with Redis handling 10,000 QPS.
    * Deployed Docker containers to GCP using automated GitHub Actions CI/CD.
    """
    profile = parse_resume_text(text)
    assert profile["candidate_name"] == "David Kim"
    assert len(profile["claims"]) >= 3
    assert len(profile["projects"]) >= 1
    assert "React" in profile["skills"] or "Fastapi" in profile["skills"]


def test_fixture_5_empty_short_resume():
    """Fixture 5: Extremely short or empty resume handled without crash."""
    empty_profile = parse_resume_text("")
    assert empty_profile["candidate_name"] == "Candidate"
    assert empty_profile["resume_score"] <= 40.0
    assert isinstance(empty_profile["skills"], list)

    short_profile = parse_resume_text("Sam Smith")
    assert short_profile["candidate_name"] == "Sam Smith"
    assert short_profile["resume_score"] <= 40.0


def test_reanalyze_resume_endpoint(client):
    """Integration test: upload resume then trigger /resume/{id}/reanalyze."""
    # 1. Upload resume
    upload_res = client.post(
        "/resume/upload",
        data={
            "raw_text": """
            Sarah Connor
            EXPERIENCE
            - Architected resilient payment gateway with FastAPI and PostgreSQL handling 5,000 TPS.
            - Implemented Redis cache reducing latency by 35%.
            SKILLS
            Python, FastAPI, PostgreSQL, Redis, Docker
            """
        }
    )
    assert upload_res.status_code == 200
    res_data = upload_res.json()
    resume_id = res_data["id"]
    assert "role_fit_scores" in res_data
    assert len(res_data["claims"]) >= 2

    # 2. Reanalyze
    reanalyze_res = client.post(f"/resume/{resume_id}/reanalyze")
    assert reanalyze_res.status_code == 200
    re_data = reanalyze_res.json()
    assert re_data["id"] == resume_id
    assert re_data["candidate_name"] == "Sarah Connor"
    assert len(re_data["claims"]) >= 2
    assert re_data["role_fit_scores"]["Backend Engineer"] >= 60.0
    assert "risk_areas" in re_data



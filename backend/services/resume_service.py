import os
import re
import json
import logging
import subprocess
import tempfile
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

KNOWN_SKILLS = {
    "Languages": [
        "python", "java", "c++", "c", "javascript", "typescript", "go", "golang",
        "rust", "c#", "php", "ruby", "kotlin", "swift", "sql", "html", "css", "bash", "shell"
    ],
    "Frameworks": [
        "react", "react.js", "next.js", "node.js", "express", "express.js",
        "fastapi", "django", "flask", "spring", "spring boot", "vue", "vue.js",
        "angular", "pytorch", "tensorflow", "keras", "pandas", "numpy", "scikit-learn"
    ],
    "Databases": [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite",
        "cassandra", "dynamodb", "elasticsearch"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
        "ci/cd", "git", "github", "gitlab", "terraform", "linux", "nginx"
    ],
    "Core Concepts": [
        "rest api", "restful", "graphql", "microservices", "agile", "scrum",
        "oop", "data structures", "algorithms", "unit testing", "system design"
    ]
}

VAGUE_PATTERNS = [
    r"responsible for\b",
    r"worked on various\b",
    r"assisted with\b",
    r"helped the team\b",
    r"handled various\b",
    r"involved in\b",
    r"tasks as assigned\b",
    r"participated in\b",
    r"did bug fixing\b",
    r"worked on daily tasks\b"
]


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using pdftotext or basic stream fallback."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(pdf_bytes)

    extracted_text = ""
    try:
        # Try system pdftotext first
        result = subprocess.run(
            ["pdftotext", tmp_path, "-"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            extracted_text = result.stdout
    except Exception as e:
        logger.warning("pdftotext execution error: %s", e)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    if not extracted_text:
        # Fallback stream regex text extraction
        try:
            raw_str = pdf_bytes.decode("latin1", errors="ignore")
            # Extract text blocks within BT ... ET
            stream_matches = re.findall(r"\((.*?)\)\s*Tj", raw_str)
            if stream_matches:
                extracted_text = " ".join(stream_matches)
            else:
                extracted_text = re.sub(r"[^\x20-\x7E\n]", " ", raw_str)
        except Exception:
            extracted_text = "Sample resume extracted text."

    return extracted_text.strip()


def parse_resume_text(text: str) -> Dict[str, Any]:
    """Parse resume text into structured candidate information with rule-based extraction."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lower_text = text.lower()

    # 1. Candidate Name Detection
    candidate_name = "Candidate"
    for line in lines[:8]:
        cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4 and not any(kw in cleaned.lower() for kw in ["resume", "curriculum", "email", "phone", "profile", "github", "linkedin", "contact", "summary"]):
            candidate_name = cleaned.title()
            break

    # 2. Extract Skills
    found_skills_categorized: Dict[str, List[str]] = {}
    flat_skills: List[str] = []

    for category, skills_list in KNOWN_SKILLS.items():
        matched = []
        for skill in skills_list:
            # Word boundary match
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
            if re.search(pattern, lower_text):
                matched.append(skill.title() if len(skill) > 3 else skill.upper())
        if matched:
            found_skills_categorized[category] = matched
            flat_skills.extend(matched)

    # 3. Extract Education
    education_lines = []
    edu_keywords = ["bachelor", "b.tech", "b.e", "master", "m.tech", "m.s", "computer science", "information technology", "university", "institute", "college", "cgpa", "gpa", "b.sc"]
    for line in lines:
        if any(kw in line.lower() for kw in edu_keywords):
            education_lines.append(line)

    education_summary = "; ".join(education_lines[:3]) if education_lines else "B.Tech / Bachelor's in Computer Science or related engineering discipline"

    # 4. Extract Experience
    exp_keywords = ["software engineer", "intern", "developer", "engineer", "lead", "architect", "analyst", "full stack", "backend", "frontend", "project", "developed", "built", "implemented"]
    experience_items = []
    for line in lines:
        if any(kw in line.lower() for kw in exp_keywords) and len(line) > 20:
            experience_items.append(line)

    experience_summary = "\n".join(experience_items[:6]) if experience_items else "Software development and engineering project experience."

    # 5. Detect Weak / Vague Statements
    weak_statements = []
    for pattern in VAGUE_PATTERNS:
        matches = re.finditer(pattern, lower_text)
        for m in matches:
            start = max(0, m.start() - 25)
            end = min(len(text), m.end() + 45)
            snippet = text[start:end].replace("\n", " ").strip()
            weak_statements.append(f"Vague expression '{m.group(0)}' in: \"...{snippet}...\"")

    has_metrics = bool(re.search(r"\b\d+%(?!\w)|\b\d+([xXkKmM]|\s*(percent|users|requests|ms|seconds|million|times))\b", lower_text))
    if not has_metrics:
        weak_statements.append("Lacks quantifiable metrics (e.g., percentages, scale, speedup, or user growth).")

    # 6. Calculate Resume Score
    # Scoring out of 100
    skills_score = min(35.0, len(flat_skills) * 4.0)
    exp_score = min(30.0, 15.0 + (len(experience_items) * 3.0))
    edu_score = 15.0 if education_lines else 10.0
    impact_score = 15.0 if has_metrics else 5.0
    clarity_penalty = min(15.0, len(weak_statements) * 3.0)
    clarity_score = max(5.0, 15.0 - clarity_penalty)

    total_score = round(min(98.0, max(45.0, skills_score + exp_score + edu_score + impact_score + clarity_score)), 1)

    # 7. Strengths, Weak Areas & Suggested Improvements
    strengths = []
    if flat_skills:
        strengths.append(f"Strong foundation in core technical competencies ({', '.join(flat_skills[:5])}).")
    if "Cloud & DevOps" in found_skills_categorized:
        strengths.append("Familiarity with DevOps/Cloud tools indicating deployment readiness.")
    if education_lines:
        strengths.append("Clear technical degree and educational credentials.")
    if len(experience_items) >= 3:
        strengths.append("Demonstrated practical development project experience.")
    if not strengths:
        strengths.append("Clear, structured resume layout with foundational technical vocabulary.")

    weak_areas = []
    if len(weak_statements) > 0:
        weak_areas.append("Contains generic or passive action descriptions without measurable ownership.")
    if not has_metrics:
        weak_areas.append("Absence of measurable outcomes (e.g. latency reduced by X%, handled Y requests).")
    if len(flat_skills) < 5:
        weak_areas.append("Relatively narrow documented technical stack; could highlight more database or testing tools.")
    if not weak_areas:
        weak_areas.append("Could further highlight system architecture and architectural tradeoffs.")

    suggested_improvements = [
        "Reframe passive bullets (e.g., 'worked on') to active impact statements (e.g., 'Architected and optimized...').",
        "Incorporate quantified business or performance impact (e.g., 'reduced API response time by 35%').",
        "Add explicit sections for system design, testing frameworks (e.g., PyTest, Jest), and deployment pipelines.",
        "Highlight problem-solving challenges and lessons learned in key project descriptions."
    ]

    summary = (
        f"{candidate_name} is a software professional with demonstrated competencies in "
        f"{', '.join(flat_skills[:4]) if flat_skills else 'software development'}. "
        f"Education background includes {education_summary[:80]}."
    )

    return {
        "candidate_name": candidate_name,
        "skills": flat_skills,
        "categorized_skills": found_skills_categorized,
        "education": education_summary,
        "experience": experience_summary,
        "resume_score": total_score,
        "strengths": strengths,
        "weak_areas": weak_areas,
        "suggested_improvements": suggested_improvements,
        "summary": summary,
        "raw_text": text
    }


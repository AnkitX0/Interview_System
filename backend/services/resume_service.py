import os
import re
import json
import logging
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple, Optional

from backend.config import ROLE_PROFILES

logger = logging.getLogger(__name__)

KNOWN_SKILLS = {
    "Languages": [
        "python", "java", "c++", "c", "javascript", "typescript", "go", "golang",
        "rust", "c#", "php", "ruby", "kotlin", "swift", "sql", "html", "css", "bash", "shell", "r"
    ],
    "Frameworks & Libraries": [
        "react", "react.js", "next.js", "node.js", "express", "express.js",
        "fastapi", "django", "flask", "spring", "spring boot", "vue", "vue.js",
        "angular", "pytorch", "tensorflow", "keras", "pandas", "numpy", "scikit-learn",
        "transformers", "huggingface", "opencv", "spacy", "langchain", "tailwind"
    ],
    "Databases & Storage": [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite",
        "cassandra", "dynamodb", "elasticsearch", "snowflake", "bigquery"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
        "ci/cd", "git", "github", "gitlab", "terraform", "ansible", "linux", "nginx",
        "helm", "prometheus", "grafana", "airflow", "kafka", "rabbitmq"
    ],
    "Core Concepts & Architecture": [
        "rest api", "restful", "graphql", "microservices", "distributed systems",
        "concurrency", "system design", "data structures", "algorithms", "unit testing",
        "oop", "etl", "machine learning", "deep learning", "nlp", "computer vision", "llm"
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
    r"worked on daily tasks\b",
    r"supported team with\b",
    r"worked on\b",
    r"explored\b",
]

BUZZWORD_PATTERNS = [
    r"\b(ai|artificial intelligence)\b",
    r"\b(blockchain|web3|crypto)\b",
    r"\b(big data)\b",
    r"\b(deep learning)\b",
    r"\b(synergy|disruptive)\b",
]

SECTION_HEADERS = {
    "summary": [r"^summary\b", r"^professional summary\b", r"^objective\b", r"^about me\b", r"^profile\b"],
    "experience": [r"^experience\b", r"^work experience\b", r"^employment\b", r"^work history\b", r"^professional experience\b"],
    "projects": [r"^projects\b", r"^technical projects\b", r"^personal projects\b", r"^key projects\b", r"^academic projects\b"],
    "skills": [r"^skills\b", r"^technical skills\b", r"^competencies\b", r"^technologies\b", r"^tools & technologies\b", r"^core competencies\b"],
    "education": [r"^education\b", r"^academic background\b", r"^qualifications\b"],
}


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using pdftotext or stream regex fallback."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(pdf_bytes)

    extracted_text = ""
    try:
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
        try:
            raw_str = pdf_bytes.decode("latin1", errors="ignore")
            stream_matches = re.findall(r"\((.*?)\)\s*Tj", raw_str)
            if stream_matches:
                extracted_text = " ".join(stream_matches)
            else:
                extracted_text = re.sub(r"[^\x20-\x7E\n]", " ", raw_str)
        except Exception:
            extracted_text = ""

    return extracted_text.strip()


def extract_pdf_page_count(pdf_bytes: bytes) -> Optional[int]:
    """Helper to extract page count from PDF using pdfinfo or regex form feed markers."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(pdf_bytes)

    page_count = None
    try:
        res = subprocess.run(["pdfinfo", tmp_path], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            for line in res.stdout.split("\n"):
                if line.startswith("Pages:"):
                    parts = line.split(":")
                    if len(parts) > 1:
                        page_count = int(parts[1].strip())
                        break
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    if page_count is None:
        ff_count = pdf_bytes.count(b"\x0c")
        if ff_count > 0:
            page_count = ff_count + 1
        else:
            page_matches = len(re.findall(b"/Type\s*/Page\b", pdf_bytes))
            if page_matches > 0:
                page_count = page_matches

    return page_count


def sanitize_resume_text(text: str) -> str:
    """Sanitizes extracted resume text to remove HTML/CSS artifacts and binary noise."""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\{[^\}]*(?:margin|padding|color|font|background|border):[^\}]*\}", " ", cleaned, flags=re.IGNORECASE)
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    return "\n".join(lines)


def validate_resume_document(text: str, filename: str = "", page_count: Optional[int] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Quality gate validating whether an extracted document is a legitimate resume/CV,
    filtering out code dumps, stack traces, HTML/CSS markup, server logs, and unrelated files.
    """
    clean_text = text.strip()
    words = clean_text.split()
    total_words = len(words)

    if total_words < 5 or len(clean_text) < 25:
        return False, "Extracted text is too short to contain resume information.", {
            "reason": "text_too_short",
            "word_count": total_words,
            "page_count": page_count,
        }

    # Negative Signal 1: High density of HTML / XML tags
    html_tags = len(re.findall(r"<[a-zA-Z\/][^>]*>", clean_text))

    # Negative Signal 2: High density of CSS styling blocks
    css_blocks = len(re.findall(r"\{[^\}]*(?:margin|padding|color|font|background|border|display):[^\}]*\}", clean_text, re.IGNORECASE))

    # Negative Signal 3: High density of source code statements & keywords
    code_patterns = [
        r"\bimport\s+java\b", r"\bpublic\s+class\b", r"\bprivate\s+void\b", r"\bSystem\.out\.print",
        r"\bString\s+url\s*=", r"\bjdbc:mysql:", r"\bfunction\s*\([^\)]*\)\s*\{", r"#include\s*<",
        r"\busing\s+namespace\b", r"\bdef\s+\w+\([^\)]*\):", r"\bconst\s+\w+\s*=\s*require\(",
        r"\bvar\s+\w+\s*=\s*new\b", r"\bval\s+\w+\s*:", r"\blet\s+\w+\s*="
    ]
    code_matches = sum(len(re.findall(pat, clean_text, re.IGNORECASE)) for pat in code_patterns)

    # Negative Signal 4: Stack traces and server logs
    log_patterns = [
        r"\bINFO:\s*", r"\bSEVERE:\s*", r"\bWARN:\s*", r"\bDEBUG:\s*", r"Server startup in \d+",
        r"Exception in thread", r"\bat com\.", r"\bat org\.", r"\bat java\.", r"Traceback \(most recent call last\):"
    ]
    log_matches = sum(len(re.findall(pat, clean_text, re.IGNORECASE)) for pat in log_patterns)

    # Negative Signal 5: SQL DDL / DML dumps
    sql_patterns = [r"\bCREATE TABLE\b", r"\bINSERT INTO\b", r"\bALTER TABLE\b", r"\bFOREIGN KEY\b"]
    sql_matches = sum(len(re.findall(pat, clean_text, re.IGNORECASE)) for pat in sql_patterns)

    total_noise_count = html_tags + css_blocks + (code_matches * 2) + (log_matches * 2) + (sql_matches * 2)

    # Positive Signal 1: Contact Info (Email, Phone, LinkedIn/GitHub)
    has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text))
    has_phone = bool(re.search(r"\+?\d[\d\s\-\(\)]{8,}\d", clean_text))
    has_link = bool(re.search(r"\b(linkedin\.com|github\.com|portfolio)\b", clean_text, re.IGNORECASE))
    contact_score = (1 if has_email else 0) + (1 if has_phone else 0) + (1 if has_link else 0)

    # Positive Signal 2: Resume Section Headers
    sections_found = 0
    header_keywords = [
        r"\b(summary|objective|profile)\b",
        r"\b(experience|work experience|employment|work history)\b",
        r"\b(projects|technical projects)\b",
        r"\b(skills|technical skills|competencies)\b",
        r"\b(education|academic background|qualifications)\b"
    ]
    for hk in header_keywords:
        if re.search(hk, clean_text, re.IGNORECASE):
            sections_found += 1

    noise_ratio = total_noise_count / max(1, total_words / 20)

    # Page count check: High page count documents (>15) require strong evidence of resume structure
    if page_count is not None and page_count >= 15:
        if sections_found < 3 or contact_score == 0:
            return False, "That document doesn't appear to be a resume. We extracted mostly code, markup, logs, or unrelated document content rather than resume information.", {
                "reason": "high_page_count_low_resume_signal",
                "page_count": page_count,
                "sections_found": sections_found,
                "contact_score": contact_score,
                "noise_count": total_noise_count,
                "detail": f"Detected {page_count} pages with high density of code/logs and low resume structure confidence."
            }

    if noise_ratio > 2.5 and (sections_found < 2 or contact_score == 0):
        return False, "That document doesn't appear to be a resume. We extracted mostly code, markup, logs, or unrelated document content rather than resume information.", {
            "reason": "high_noise_density",
            "noise_ratio": round(noise_ratio, 2),
            "sections_found": sections_found,
            "contact_score": contact_score,
            "detail": "High density of source code, HTML/CSS markup, SQL, or server logs detected."
        }

    return True, "Valid resume document", {
        "page_count": page_count,
        "sections_found": sections_found,
        "contact_score": contact_score,
        "noise_ratio": round(noise_ratio, 2)
    }


def split_resume_into_sections(text: str) -> Dict[str, List[str]]:
    """
    Splits resume text into labeled sections based on standard section headings,
    with fallback unheaded lines preserved.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    sections: Dict[str, List[str]] = {
        "summary": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "education": [],
        "unheaded": [],
    }

    current_section = "unheaded"

    for line in lines:
        cleaned_header = re.sub(r"[:\-_#*]+", "", line).strip().lower()
        matched_section = None
        for sec_name, patterns in SECTION_HEADERS.items():
            if any(re.match(p, cleaned_header, re.IGNORECASE) for p in patterns):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
            continue

        # Strip standard bullet characters
        clean_line = re.sub(r"^[•\*\-\–\—\d+\.]\s*", "", line).strip()
        if clean_line:
            sections[current_section].append(clean_line)

    return sections


def extract_skills_detailed(lower_text: str) -> Tuple[List[str], Dict[str, List[str]], List[Dict[str, Any]]]:
    """
    Extracts flat skills, categorized skills, and granular ResumeSkill schema objects.
    """
    found_categorized: Dict[str, List[str]] = {}
    flat_skills: List[str] = []
    skills_detailed: List[Dict[str, Any]] = []

    for category, skills_list in KNOWN_SKILLS.items():
        matched = []
        for skill in skills_list:
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
            match = re.search(pattern, lower_text)
            if match:
                display_name = skill.title() if len(skill) > 3 else skill.upper()
                matched.append(display_name)
                flat_skills.append(display_name)
                # Check if evidenced in sentences beyond bare comma lists
                surrounding = lower_text[max(0, match.start() - 30):min(len(lower_text), match.end() + 30)]
                has_action_words = bool(re.search(r"\b(built|used|developed|deployed|trained|designed|implemented|optimized|tested)\b", surrounding))
                skills_detailed.append({
                    "name": display_name,
                    "category": category,
                    "confidence": 0.95 if has_action_words else 0.80,
                    "evidenced": has_action_words,
                })
        if matched:
            found_categorized[category] = matched

    return flat_skills, found_categorized, skills_detailed


def extract_projects_and_claims(
    sections: Dict[str, List[str]],
    raw_text: str,
    detected_skills: List[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts projects and individual claims with probe priorities and rationale.
    """
    projects: List[Dict[str, Any]] = []
    claims: List[Dict[str, Any]] = []

    candidate_lines = []
    # Collect bullets from projects, experience, and unheaded lines
    candidate_lines.extend(sections.get("projects", []))
    candidate_lines.extend(sections.get("experience", []))
    if not candidate_lines:
        candidate_lines.extend(sections.get("unheaded", []))

    # Also detect action-oriented bullets across entire text if still empty
    if not candidate_lines:
        action_verb_re = re.compile(r"^(built|developed|designed|implemented|architected|engineered|led|created|optimized|deployed|trained|scaled)\b", re.IGNORECASE)
        for line in raw_text.split("\n"):
            clean = re.sub(r"^[•\*\-\–\—\d+\.]\s*", "", line.strip())
            if clean and (action_verb_re.match(clean) or len(clean) > 25):
                candidate_lines.append(clean)

    # Synthesize projects from project section or group bullets
    project_lines = sections.get("projects", [])
    if project_lines:
        # Group into projects
        current_proj = None
        for line in project_lines:
            if len(line) < 45 and not line.endswith(".") and not any(line.lower().startswith(p) for p in ["built", "developed", "used", "created"]):
                # Likely a project title
                if current_proj:
                    projects.append(current_proj)
                current_proj = {
                    "title": line,
                    "description": "",
                    "technologies": [],
                    "bullets": []
                }
            else:
                if not current_proj:
                    current_proj = {
                        "title": "Technical Project",
                        "description": "",
                        "technologies": [],
                        "bullets": []
                    }
                current_proj["bullets"].append(line)
                matched_tech = [s for s in detected_skills if s.lower() in line.lower()]
                current_proj["technologies"] = list(set(current_proj["technologies"] + matched_tech))
        if current_proj:
            projects.append(current_proj)

    if not projects and candidate_lines:
        # Create default project grouping
        all_tech = [s for s in detected_skills if any(s.lower() in cl.lower() for cl in candidate_lines)]
        projects.append({
            "title": "Primary Engineering Experience",
            "description": "Core software development and system implementation accomplishments.",
            "technologies": all_tech[:6],
            "bullets": candidate_lines[:6]
        })

    # Metric pattern
    metric_pattern = re.compile(
        r"(\b\d+(\.\d+)?%|\b\d+(\.\d+)?[xX]\b|\b\d+\s*(ms|seconds|minutes|hours|users|requests|tps|qps|rps|mb|gb|tb|million|billion|pods|nodes|k\b)|\$[\d,]+|\b\d+\+)",
        re.IGNORECASE
    )

    # Extract individual claims from all candidate lines
    for line in candidate_lines:
        if len(line) < 15:
            continue

        has_metric = bool(metric_pattern.search(line))
        matched_tech = [s for s in detected_skills if s.lower() in line.lower()]

        # Determine claim type
        line_lower = line.lower()
        if any(w in line_lower for w in ["architect", "pipeline", "distributed", "microservice", "infrastructure", "cache", "system design", "concurrency"]):
            claim_type = "architecture"
        elif any(w in line_lower for w in ["scaled", "scale", "million", "throughput", "concurrency", "qps", "load"]):
            claim_type = "scale"
        elif any(w in line_lower for w in ["led", "founded", "architected", "headed", "managed", "owned", "spearheaded"]):
            claim_type = "ownership"
        elif has_metric:
            claim_type = "metric"
        else:
            claim_type = "general"

        # Calculate probe priority
        priority = 0.5
        reasons = []

        if has_metric:
            priority += 0.25
            reasons.append("Contains quantified performance or outcome metric (+0.25)")
        if claim_type in ("architecture", "scale", "ownership"):
            priority += 0.15
            reasons.append(f"High-impact {claim_type} statement (+0.15)")
        if matched_tech:
            priority += min(0.15, len(matched_tech) * 0.05)
            reasons.append(f"Grounded in specific technical skills: {', '.join(matched_tech)}")

        # Check for vague wording penalty
        is_vague = any(re.search(pat, line_lower) for pat in VAGUE_PATTERNS)
        if is_vague and not has_metric:
            priority -= 0.20
            reasons.append("Vague action description without concrete outcome (-0.20)")

        priority = round(max(0.1, min(1.0, priority)), 2)

        claims.append({
            "claim_text": line,
            "claim_type": claim_type,
            "technologies": matched_tech,
            "has_metric": has_metric,
            "probe_priority": priority,
            "reasons": reasons,
            "project_idx": 0 if projects else None,
        })

    return projects, claims


def extract_resume_flags(
    claims: List[Dict[str, Any]],
    skills: List[str],
    raw_text: str
) -> List[Dict[str, Any]]:
    """
    Extracts audit flags with severity ratings.
    """
    flags = []
    seen_descriptions = set()

    # 1. Vague claims
    for idx, c in enumerate(claims):
        text = c["claim_text"].lower()
        for pattern in VAGUE_PATTERNS:
            if re.search(pattern, text) and not c["has_metric"]:
                desc = f"Passive or vague expression '{re.search(pattern, text).group(0)}' in: \"{c['claim_text'][:70]}...\""
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    flags.append({
                        "flag_type": "vague_claim",
                        "description": desc,
                        "severity": "medium",
                        "claim_idx": idx,
                    })

    # 2. Buzzword without context
    for idx, c in enumerate(claims):
        text = c["claim_text"].lower()
        if len(c["claim_text"]) < 50:
            for pattern in BUZZWORD_PATTERNS:
                m = re.search(pattern, text)
                if m and len(c["technologies"]) == 0:
                    desc = f"Mentions buzzword '{m.group(0)}' without concrete technical context or implementation details."
                    if desc not in seen_descriptions:
                        seen_descriptions.add(desc)
                        flags.append({
                            "flag_type": "buzzword_without_context",
                            "description": desc,
                            "severity": "low",
                            "claim_idx": idx,
                        })

    # 3. Unsupported metric
    for idx, c in enumerate(claims):
        if c["has_metric"] and len(c["technologies"]) == 0:
            desc = f"Claims performance or business metric without specifying the underlying mechanism or baseline: \"{c['claim_text'][:70]}...\""
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                flags.append({
                    "flag_type": "unsupported_metric",
                    "description": desc,
                    "severity": "medium",
                    "claim_idx": idx,
                })

    # 4. Sparse skills (listed skills never evidenced in any claim or project)
    claims_text_corpus = " ".join(c["claim_text"].lower() for c in claims)
    for skill in skills:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        if not re.search(pattern, claims_text_corpus):
            desc = f"Skill '{skill}' is declared but not referenced in any project or experience accomplishment."
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                flags.append({
                    "flag_type": "sparse_skills",
                    "description": desc,
                    "severity": "info",
                    "claim_idx": None,
                })

    return flags


def calculate_role_fit_scores(
    skills: List[str],
    claims: List[Dict[str, Any]],
    raw_text: str
) -> Dict[str, float]:
    """
    Computes candidate role fit scores (0-100) across curated role profiles.
    """
    role_fits: Dict[str, float] = {}
    lower_text = raw_text.lower()
    claims_text = " ".join(c["claim_text"].lower() for c in claims)

    words = len(raw_text.split())
    if words < 10:
        return {role: 0.0 for role in ROLE_PROFILES}

    for role_name, profile in ROLE_PROFILES.items():
        core_skills = profile["core_skills"]
        keywords = profile.get("keywords", [])

        # Skill match
        matched_skills = [s for s in skills if s.lower() in core_skills]
        # Target threshold: 6 matching skills gives high coverage
        skill_ratio = min(1.0, len(matched_skills) / 6.0)
        skill_score = skill_ratio * 60.0

        # Keyword match in experience and claims
        matched_kws = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", lower_text))
        kw_ratio = min(1.0, matched_kws / max(len(keywords) * 0.4, 1.0))
        kw_score = kw_ratio * 40.0

        total_score = round(min(98.0, max(15.0, skill_score + kw_score)), 1)
        role_fits[role_name] = total_score

    return role_fits


def identify_risk_areas(
    flags: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
    role_fits: Dict[str, float]
) -> List[str]:
    """
    Synthesizes overarching candidate risk areas for interviewer probing.
    """
    risks = []
    vague_flags = [f for f in flags if f["flag_type"] == "vague_claim"]
    unsupported = [f for f in flags if f["flag_type"] == "unsupported_metric"]
    sparse = [f for f in flags if f["flag_type"] == "sparse_skills"]

    if len(vague_flags) >= 2:
        risks.append(f"Multiple project accomplishments ({len(vague_flags)}) use passive phrasing without clear individual ownership.")
    if unsupported:
        risks.append("Quantified performance gains are cited without detailing the profiling methodology or technical mechanism.")
    if len(sparse) >= 3:
        sparse_names = [s["description"].split("'")[1] if "'" in s["description"] else "skills" for s in sparse[:3]]
        risks.append(f"Several listed competencies ({', '.join(sparse_names)}) lack practical project evidence.")
    if not any(c["has_metric"] for c in claims):
        risks.append("Absence of measurable engineering outcomes (latency, throughput, cost, scale).")

    # If role fit for Backend Engineer is low
    if role_fits.get("Backend Engineer", 0.0) < 40.0:
        risks.append("Limited documented depth in database design, concurrency, and system architecture.")

    if not risks:
        risks.append("Solid technical evidence; probe technical edge cases and failure modes.")

    return risks[:4]


def parse_resume_text(text: str) -> Dict[str, Any]:
    """
    Comprehensive resume parsing and intelligence analysis pipeline.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lower_text = text.lower()

    # 1. Candidate Name Detection
    candidate_name = "Candidate"
    for line in lines[:8]:
        cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip()
        cleaned = re.sub(r"^(dr|mr|ms|mrs|prof)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4 and not any(kw in cleaned.lower() for kw in ["resume", "curriculum", "email", "phone", "profile", "github", "linkedin", "contact", "summary"]):
            candidate_name = cleaned.title()
            break

    # 2. Section Parsing
    sections = split_resume_into_sections(text)

    # 3. Extract Skills (Flat, Categorized, Detailed)
    flat_skills, categorized_skills, skills_detailed = extract_skills_detailed(lower_text)

    # 4. Extract Education
    education_lines = sections.get("education", [])
    if not education_lines:
        edu_keywords = ["bachelor", "b.tech", "b.e", "master", "m.tech", "m.s", "computer science", "university", "institute", "college", "gpa"]
        for line in lines:
            if any(kw in line.lower() for kw in edu_keywords):
                education_lines.append(line)
    education_summary = "; ".join(education_lines[:3]) if education_lines else "B.Tech / Bachelor's in Computer Science or related engineering discipline"

    # 5. Extract Projects and Claims
    projects, claims = extract_projects_and_claims(sections, text, flat_skills)

    # 6. Extract Audit Flags
    flags = extract_resume_flags(claims, flat_skills, text)

    # 7. Role Fit Scores
    role_fit_scores = calculate_role_fit_scores(flat_skills, claims, text)

    # 8. Verification Risk Areas
    risk_areas = identify_risk_areas(flags, claims, role_fit_scores)

    # 9. Overall Resume Score
    has_metrics = any(c["has_metric"] for c in claims)
    skills_score = min(35.0, len(flat_skills) * 3.5)
    exp_score = min(30.0, 15.0 + (len(claims) * 2.5))
    edu_score = 15.0 if education_lines else 10.0
    impact_score = 15.0 if has_metrics else 5.0
    clarity_penalty = min(15.0, len([f for f in flags if f["severity"] in ("medium", "high")]) * 3.0)
    clarity_score = max(5.0, 15.0 - clarity_penalty)

    words = len(text.split())
    if words < 15:
        total_score = 30.0
    else:
        total_score = round(min(98.0, max(40.0, skills_score + exp_score + edu_score + impact_score + clarity_score)), 1)

    # Experience summary
    experience_lines = sections.get("experience", [])
    if not experience_lines and claims:
        experience_lines = [c["claim_text"] for c in claims[:4]]
    experience_summary = "\n".join(experience_lines[:6]) if experience_lines else "Software development and engineering project experience."

    # Strengths
    strengths = []
    if flat_skills:
        strengths.append(f"Strong foundation in core technical competencies ({', '.join(flat_skills[:5])}).")
    if "Cloud & DevOps" in categorized_skills:
        strengths.append("Familiarity with DevOps/Cloud tools indicating deployment readiness.")
    if has_metrics:
        strengths.append("Contains quantified performance and business impact indicators.")
    if len(claims) >= 3:
        strengths.append("Demonstrated practical implementation and architecture experience.")
    if not strengths:
        strengths.append("Foundational technical background with clear career intent.")

    # Weak areas
    weak_areas = []
    if any(f["flag_type"] == "vague_claim" for f in flags):
        weak_areas.append("Contains generic or passive action descriptions without clear individual ownership.")
    if not has_metrics:
        weak_areas.append("Absence of measurable outcomes (e.g. latency reduced by X%, handled Y requests).")
    if len(flat_skills) < 5:
        weak_areas.append("Relatively narrow documented technical stack; could highlight more database or testing tools.")
    if not weak_areas:
        weak_areas.append("Could further highlight system architecture and architectural tradeoffs.")

    suggested_improvements = [
        "Reframe passive bullets to active impact statements (e.g., 'Architected and optimized...').",
        "Incorporate quantified business or performance impact (e.g., 'reduced API response time by 35%').",
        "Add explicit sections for system design, testing frameworks (e.g., PyTest, Jest), and deployment pipelines.",
        "Highlight problem-solving challenges and lessons learned in key project descriptions."
    ]

    summary = (
        f"{candidate_name} is a software professional with demonstrated competencies in "
        f"{', '.join(flat_skills[:4]) if flat_skills else 'software engineering'}. "
        f"Education background includes {education_summary[:80]}."
    )

    return {
        "candidate_name": candidate_name,
        "skills": flat_skills,
        "categorized_skills": categorized_skills,
        "skills_detailed": skills_detailed,
        "education": education_summary,
        "experience": experience_summary,
        "projects": projects,
        "claims": claims,
        "flags": flags,
        "role_fit_scores": role_fit_scores,
        "risk_areas": risk_areas,
        "resume_score": total_score,
        "strengths": strengths,
        "weak_areas": weak_areas,
        "suggested_improvements": suggested_improvements,
        "summary": summary,
        "raw_text": text
    }

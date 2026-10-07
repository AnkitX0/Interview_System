"""
backend/services/answer_study_service.py
Structured Answer Review & Comparative Teaching Engine.
Produces qualitative comparison for candidate review:
- Candidate Answer vs Expected Strong Concepts
- Missing points based on actual submission
- Polished improved answer
- Genuine resume connection (strictly grounded in actual candidate resume)
- Next practice drill prompt
"""

import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.services.llm_gemini_service import call_gemini_json

logger = logging.getLogger("interview_system.answer_study")


class StudyAnalysisOutput(BaseModel):
    answer_status: str = Field(..., description="STRONG | PARTIAL | WEAK | INSUFFICIENT | EMPTY | SKIPPED")
    strong_answer_should_cover: List[str] = Field(default_factory=list)
    missing_points: List[str] = Field(default_factory=list)
    improved_answer: str = Field(default="")
    resume_connection: Optional[str] = None
    practice_prompt: Optional[str] = None


# Knowledge base of expected technical/behavioral concepts for common topics
TOPIC_EXPECTATIONS = {
    "api versioning": {
        "should_cover": [
            "Necessity of versioning to prevent breaking live consumers and downstream microservices",
            "Versioning mechanisms: URI path (/v1/), custom headers (X-API-Version), or query params",
            "Backward compatibility guarantees and deprecation timelines with sunset headers",
            "Schema migration strategies for supporting both legacy and current clients simultaneously",
            "Operational trade-offs: code duplication vs conditional routing complexity"
        ],
        "improved": (
            "A strong response establishes that API versioning prevents breaking contract changes for downstream clients. "
            "You should contrast URI path versioning (/api/v1/) against header-based routing, explain your deprecation lifecycle "
            "(e.g., maintaining dual support with sunset headers), and discuss the maintenance trade-off of maintaining multiple route handlers."
        ),
        "practice": "Design an API versioning and deprecation migration plan for a public payment API used by 50,000 external merchants."
    },
    "rest api": {
        "should_cover": [
            "Core architectural constraints: statelessness, client-server decoupling, cacheability",
            "Semantic utilization of HTTP verbs (GET, POST, PUT, PATCH, DELETE) and idempotent operations",
            "Standard HTTP status code hierarchies (2xx success, 4xx client errors, 5xx server faults)",
            "Resource-oriented URI design vs RPC action-oriented endpoints",
            "Stateless authentication via Bearer tokens or JWTs"
        ],
        "improved": (
            "A comprehensive REST response explains client-server decoupling and statelessness, meaning every request must contain "
            "complete context. It details resource naming conventions, idempotent operations (PUT/DELETE), and distinguishes "
            "proper error communication using semantic 4xx vs 5xx status codes."
        ),
        "practice": "Explain how you would design an idempotent REST endpoint for financial transactions to guarantee zero duplicate charges."
    },
    "database": {
        "should_cover": [
            "Access patterns and query characteristics (read-heavy vs write-heavy workloads)",
            "Relational ACID transactions vs NoSQL horizontal partition scaling",
            "Indexing strategies (B-Tree, Hash, GIN) and write amplification penalties",
            "Connection pooling (PgBouncer, HikariCP) and query execution plans",
            "Data consistency models and failover strategies"
        ],
        "improved": (
            "A strong answer articulates workload characteristics (read vs write ratios) and compares relational schemas with ACID guarantees "
            "against NoSQL documents. It demonstrates depth by discussing B-Tree indexing, execution plan optimization (EXPLAIN ANALYZE), "
            "and mitigating connection limits via pooling."
        ),
        "practice": "How would you optimize a database query running on a 20-million row table that is currently causing p99 latency spikes?"
    },
    "acid": {
        "should_cover": [
            "Atomicity: all-or-nothing transaction execution via Write-Ahead Logging (WAL) and rollbacks",
            "Consistency: preserving database schema constraints, foreign keys, and invariants",
            "Isolation: preventing concurrent anomalies across isolation levels (Read Committed, Repeatable Read, Serializable)",
            "Durability: committed state surviving hardware crashes through non-volatile disk flush (fsync)",
            "Concurrency trade-offs between lock contention and dirty/phantom reads"
        ],
        "improved": (
            "A strong response breaks down all four pillars: Atomicity via write-ahead logging rollbacks, Consistency via schema constraints, "
            "Isolation through transaction isolation levels and lock mechanisms, and Durability through disk sync (fsync). "
            "It emphasizes the performance penalty of stricter isolation levels like Serializable."
        ),
        "practice": "Explain what isolation level you would select for an inventory reservation system to prevent overselling while maximizing throughput."
    },
    "microservices": {
        "should_cover": [
            "Domain-driven bounded contexts and independent service deployment",
            "Inter-service communication: synchronous gRPC/REST vs asynchronous event streams (Kafka/RabbitMQ)",
            "Data isolation per service and managing distributed transactions (Saga pattern)",
            "Resilience patterns: circuit breakers, timeouts, retries with exponential backoff",
            "Operational observability: distributed tracing, centralized logging, and health probes"
        ],
        "improved": (
            "A strong response defines microservices through domain boundaries and database-per-service isolation. "
            "It addresses distributed systems realities by contrasting synchronous REST with asynchronous event choreography, "
            "and explains resilience using circuit breakers and distributed tracing."
        ),
        "practice": "How would you handle a distributed transaction across three microservices without using two-phase commit?"
    },
    "cache": {
        "should_cover": [
            "Caching topologies (in-memory Redis/Memcached vs CDN edge caching)",
            "Caching strategies: Cache-Aside, Write-Through, Write-Behind",
            "Cache invalidation mechanics, TTL policies, and eviction algorithms (LRU, LFU)",
            "System failure modes: cache penetration, cache stampede (thundering herd), and cache avalanche",
            "Mitigation strategies: mutex locks, probabilistic early expiration, and pre-warming"
        ],
        "improved": (
            "An expert answer contrasts Cache-Aside with Write-Through patterns, outlines Redis key expiration TTLs, "
            "and directly addresses production failure modes like cache stampedes using distributed locks or background probabilistic refresh."
        ),
        "practice": "Describe how you would protect your database from a thundering herd when a high-traffic cache key expires simultaneously."
    },
}


def _classify_answer_status(transcript: str) -> str:
    """Classifies candidate submission into strict evidence categories."""
    text = (transcript or "").strip()
    if not text or text == "[SKIPPED]":
        return "SKIPPED" if text == "[SKIPPED]" else "EMPTY"
    
    words = text.split()
    lower = text.lower()
    
    trivial_markers = {"idk", "i don't know", "idk.", "no", "yes", "skip", "none", "pass", "na", "n/a", "dsjnd", "test", "asdf"}
    if len(words) < 4 or lower in trivial_markers:
        return "INSUFFICIENT"
    
    if len(words) < 15:
        return "WEAK"
    elif len(words) < 50:
        return "PARTIAL"
    else:
        return "STRONG"


def _find_matching_topic(question_text: str) -> Optional[str]:
    """Finds closest matching conceptual topic from question text."""
    q_lower = (question_text or "").lower()
    for topic in TOPIC_EXPECTATIONS.keys():
        if topic in q_lower:
            return topic
    return None


TECH_DOMAIN_MAP: Dict[str, List[str]] = {
    "api": ["fastapi", "flask", "django", "express", "nestjs", "rest", "graphql", "spring", "api"],
    "rest": ["fastapi", "flask", "django", "express", "nestjs", "spring", "rest"],
    "backend": ["fastapi", "flask", "django", "express", "spring", "golang", "node", "python", "backend"],
    "database": ["postgresql", "postgres", "mysql", "mongodb", "redis", "dynamodb", "sql", "db"],
    "sql": ["postgresql", "postgres", "mysql", "sqlite", "sql"],
    "cache": ["redis", "memcached"],
    "caching": ["redis", "memcached"],
    "docker": ["docker", "container", "kubernetes"],
    "container": ["docker", "kubernetes"],
    "concurrency": ["threading", "asyncio", "goroutines", "distributed", "multiprocessing"],
}


def _derive_grounded_resume_connection(
    question_text: str,
    resume_skills: Optional[List[str]],
    resume_projects: Optional[List[Dict[str, Any]]]
) -> Optional[str]:
    """
    Connects the interview question to actual candidate resume evidence.
    STRICT RULE: Only returns a connection when supported by genuine resume data.
    Never fabricates unlisted projects or skills.
    """
    if not resume_skills and not resume_projects:
        return None

    q_lower = (question_text or "").lower()
    q_words = set(w.strip("?,.:;()[]\"'") for w in q_lower.split() if len(w) >= 3)

    matched_skills = []
    if resume_skills:
        for skill in resume_skills:
            s_low = skill.lower()
            if s_low in q_lower:
                matched_skills.append(skill)
                continue
            # Check domain mapping
            for q_word in q_words:
                if q_word in TECH_DOMAIN_MAP and any(alias in s_low for alias in TECH_DOMAIN_MAP[q_word]):
                    if skill not in matched_skills:
                        matched_skills.append(skill)

    matched_projects = []
    if resume_projects:
        for p in resume_projects:
            title = p.get("title", "")
            desc = p.get("description", "")
            techs = p.get("technologies", [])
            text_block = f"{title} {desc} {' '.join(techs)}".lower()
            # Match directly or via techs
            if any(term in text_block for term in q_words if len(term) >= 4):
                matched_projects.append(title)
            elif any(s in techs for s in matched_skills):
                if title not in matched_projects:
                    matched_projects.append(title)

    if matched_projects and matched_skills:
        return (
            f"You featured '{matched_projects[0]}' utilizing {matched_skills[0]} on your resume. "
            f"A strong answer should connect this question to how you implemented and maintained systems in that project."
        )
    elif matched_projects:
        return (
            f"This relates directly to your project '{matched_projects[0]}'. "
            f"Ground your answer in your implementation decisions and production trade-offs from that project."
        )
    elif matched_skills:
        return (
            f"You declared competency in {', '.join(matched_skills[:2])} on your profile. "
            f"Ensure you discuss the idioms, conventions, and operational characteristics of {matched_skills[0]} when answering."
        )

    return None


def generate_study_comparison_for_answer(
    question_text: str,
    candidate_answer: str,
    category: str = "Technical",
    resume_skills: Optional[List[str]] = None,
    resume_projects: Optional[List[Dict[str, Any]]] = None,
    target_role: str = "Software Engineer"
) -> Dict[str, Any]:
    """
    Produces complete, evidence-gated comparative analysis for the candidate report.
    Tries structured Gemini LLM when available; falls back to deterministic curriculum mapping.
    """
    raw_text = (candidate_answer or "").strip()
    status = _classify_answer_status(raw_text)

    # 1. Skipped Answer
    if status == "SKIPPED":
        matched_topic = _find_matching_topic(question_text)
        topic_info = TOPIC_EXPECTATIONS.get(matched_topic, {}) if matched_topic else {}
        should_cover = topic_info.get("should_cover", [
            f"Core conceptual definition and purpose for {category.lower()} domain",
            "Underlying engineering mechanisms or structured rationale",
            "System trade-offs, edge cases, and architectural alternatives",
            "Concrete examples demonstrating hands-on implementation ownership"
        ])
        return {
            "answer_status": "SKIPPED",
            "status_label": "Skipped Question",
            "strong_answer_should_cover": should_cover,
            "missing_points": ["Candidate chose not to answer; no evidence collected."],
            "improved_answer": topic_info.get(
                "improved",
                f"A strong answer clearly addresses {question_text[:60]}... by framing the core problem, explaining the underlying mechanism, and contrasting architectural alternatives."
            ),
            "resume_connection": _derive_grounded_resume_connection(question_text, resume_skills, resume_projects),
            "practice_prompt": topic_info.get("practice", f"Practice explaining: {question_text}")
        }

    # 2. Empty Answer
    if status == "EMPTY":
        matched_topic = _find_matching_topic(question_text)
        topic_info = TOPIC_EXPECTATIONS.get(matched_topic, {}) if matched_topic else {}
        return {
            "answer_status": "EMPTY",
            "status_label": "Empty Submission",
            "strong_answer_should_cover": topic_info.get("should_cover", [
                "Direct explanation of the concept or scenario",
                "Technical mechanisms and implementation specifics",
                "Trade-offs and architectural constraints",
                "Measurable engineering outcomes"
            ]),
            "missing_points": [
                "No answer text submitted",
                "Zero technical mechanisms or reasoning provided",
                "Missing concrete examples"
            ],
            "improved_answer": topic_info.get("improved", "A complete response addresses the question directly with concrete implementation details and engineering trade-offs."),
            "resume_connection": _derive_grounded_resume_connection(question_text, resume_skills, resume_projects),
            "practice_prompt": topic_info.get("practice", f"Practice answering: {question_text}")
        }

    # 3. Insufficient / Trivial Answer
    if status == "INSUFFICIENT":
        matched_topic = _find_matching_topic(question_text)
        topic_info = TOPIC_EXPECTATIONS.get(matched_topic, {}) if matched_topic else {}
        return {
            "answer_status": "INSUFFICIENT",
            "status_label": "Insufficient Response",
            "strong_answer_should_cover": topic_info.get("should_cover", [
                "Clear definition and purpose of the architectural concept",
                "Concrete technical implementation mechanisms",
                "Comparative analysis of alternative approaches",
                "Production constraints and failure handling"
            ]),
            "missing_points": [
                "Submitted text lacks explanatory depth (only brief or single-word token)",
                "No technical terminology or mechanisms provided",
                "Missing justification or personal implementation ownership"
            ],
            "improved_answer": topic_info.get("improved", "Elaborate with specific mechanisms, architecture diagrams, and personal experience rather than brief placeholders."),
            "resume_connection": _derive_grounded_resume_connection(question_text, resume_skills, resume_projects),
            "practice_prompt": topic_info.get("practice", f"Practice formulating a 90-second technical answer for: {question_text}")
        }

    # 4. Meaningful Answer: Attempt Gemini qualitative review if configured
    resume_context_snippet = ""
    if resume_skills:
        resume_context_snippet += f"Candidate Verified Skills: {', '.join(resume_skills[:6])}\n"
    if resume_projects:
        proj_titles = [p.get('title', '') for p in resume_projects if p.get('title')]
        if proj_titles:
            resume_context_snippet += f"Candidate Projects: {', '.join(proj_titles[:3])}\n"

    prompt = (
        f"Role: {target_role}\n"
        f"Category: {category}\n"
        f"Interviewer Question: {question_text}\n"
        f"Candidate Submission: {raw_text}\n"
        f"{resume_context_snippet}\n"
        "Provide a structured educational critique comparing the candidate's answer against an ideal response.\n"
        "RULES:\n"
        "1. answer_status: choose STRONG, PARTIAL, or WEAK.\n"
        "2. strong_answer_should_cover: 3-5 concise bullet points of concepts an ideal answer must include.\n"
        "3. missing_points: 2-4 specific concepts the candidate missed or explained poorly.\n"
        "4. improved_answer: a concise, high-scoring model response (3-5 sentences).\n"
        "5. resume_connection: ONLY reference genuine technologies/projects from the provided candidate context if relevant; otherwise return null. NEVER invent project facts.\n"
        "6. practice_prompt: a targeted drill question to reinforce this specific topic.\n\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "answer_status": "STRONG|PARTIAL|WEAK",\n'
        '  "strong_answer_should_cover": ["point 1", "point 2"],\n'
        '  "missing_points": ["missing 1", "missing 2"],\n'
        '  "improved_answer": "...",\n'
        '  "resume_connection": "string or null",\n'
        '  "practice_prompt": "..."\n'
        "}"
    )

    llm_res = call_gemini_json(prompt, timeout=3.5)
    if llm_res:
        try:
            parsed = StudyAnalysisOutput(**llm_res)
            return {
                "answer_status": parsed.answer_status.upper(),
                "status_label": f"{parsed.answer_status.title()} Answer",
                "strong_answer_should_cover": parsed.strong_answer_should_cover,
                "missing_points": parsed.missing_points,
                "improved_answer": parsed.improved_answer,
                "resume_connection": parsed.resume_connection or _derive_grounded_resume_connection(question_text, resume_skills, resume_projects),
                "practice_prompt": parsed.practice_prompt
            }
        except Exception as e:
            logger.warning("StudyAnalysisOutput parse warning: %s", e)

    # Deterministic fallback when Gemini is not configured or times out
    matched_topic = _find_matching_topic(question_text)
    topic_info = TOPIC_EXPECTATIONS.get(matched_topic, {}) if matched_topic else {}

    missing_points = []
    lower_ans = raw_text.lower()
    if not any(k in lower_ans for k in ["because", "due to", "tradeoff", "therefore"]):
        missing_points.append("Lacks technical justification and causal trade-offs.")
    if not any(k in lower_ans for k in ["latency", "throughput", "scale", "performance", "%", "ms"]):
        missing_points.append("Did not quantify scale, latency limits, or performance metrics.")
    if len(raw_text.split()) < 40:
        missing_points.append("Response is brief; misses edge cases and failure mode recovery.")
    if not missing_points:
        missing_points.append("Could further articulate alternative architectural approaches considered.")

    return {
        "answer_status": status,
        "status_label": f"{status.title()} Answer",
        "strong_answer_should_cover": topic_info.get("should_cover", [
            "Core architectural mechanism and protocol behavior",
            "Data flow and state transition guarantees",
            "Operational trade-offs and performance implications",
            "Failure mode mitigation and resilience patterns"
        ]),
        "missing_points": missing_points,
        "improved_answer": topic_info.get(
            "improved",
            f"Structure your response to {question_text[:50]}... by stating the core mechanism first, explaining the system trade-offs, and verifying reliability with concrete engineering metrics."
        ),
        "resume_connection": _derive_grounded_resume_connection(question_text, resume_skills, resume_projects),
        "practice_prompt": topic_info.get("practice", f"Explain how you would handle production edge cases for: {question_text}")
    }

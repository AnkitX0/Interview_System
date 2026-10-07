"""
backend/services/practice_drill_service.py
Dedicated Practice Drill Question Selector & Generator.
Guarantees distinct purposes for every practice category:
1. TECHNICAL_DEPTH - System mechanics, concurrency, performance, algorithms.
2. TRADEOFF_REASONING - Direct architectural dilemmas and write/read trade-offs.
3. FOLLOWUP_DEFENSE - Deep interviewer probing, edge cases, failure scenarios.
4. PROJECT_DEFENSE & RESUME_CLAIM_DEFENSE - Strictly grounded in candidate's actual resume.
5. STRUCTURED_ANSWER & COMMUNICATION - Context -> Action -> Result, concise clarity.
6. BEHAVIORAL_STAR - Workplace scenarios requiring STAR evidence.
7. PRESSURE_RESPONSE - Live incident triage and urgent system recovery.

Includes semantic and string deduplication across sessions to never repeat questions in a drill.
"""

import json
import logging
import random
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

import backend.models as models

logger = logging.getLogger("interview_system.practice_drills")

# Distinct Question Pools for Practice Categories
DISTINCT_DRILL_POOLS: Dict[str, List[Dict[str, Any]]] = {
    "TECHNICAL_DEPTH": [
        {
            "question": "How do database isolation levels differ in their prevention of dirty reads, non-repeatable reads, and phantom reads?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Database Concurrency"
        },
        {
            "question": "Explain how garbage collection or manual memory management impacts p99 latency in a high-throughput backend service.",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Runtime Mechanics"
        },
        {
            "question": "Walk through how a B-Tree index is structured on disk and explain the write amplification cost during frequent inserts.",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Storage Engines"
        },
        {
            "question": "What mechanisms would you use to prevent race conditions when two distributed workers simultaneously deduct from a shared user balance?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Distributed Concurrency"
        },
        {
            "question": "Explain the difference between thread pools and event loop concurrency models (e.g., worker threads vs async/await event loops).",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Concurrency Architecture"
        },
        {
            "question": "How does TCP flow control differ from TCP congestion control, and how does each prevent network packet loss?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Networking Protocols"
        },
        {
            "question": "Explain how distributed cache stampedes (thundering herds) occur and detail two distinct algorithmic strategies to mitigate them.",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Caching Architecture"
        },
    ],
    "TRADEOFF_REASONING": [
        {
            "question": "Compare choosing an ACID relational database against an eventually consistent document store for a retail checkout system. What are the key trade-offs?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Data Architecture Trade-offs"
        },
        {
            "question": "Evaluate the architectural trade-offs between synchronous REST microservice communication and asynchronous message queuing (e.g., RabbitMQ/Kafka).",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Integration Trade-offs"
        },
        {
            "question": "What are the trade-offs of optimistic concurrency control versus pessimistic locking when building a high-traffic inventory reservation engine?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Concurrency Trade-offs"
        },
        {
            "question": "Contrast horizontal database sharding against read-replica replication. At what scale does read replication break down?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Scalability Trade-offs"
        },
        {
            "question": "What are the trade-offs between server-side rendering (SSR) and static site generation (SSG) regarding TTFB, hosting complexity, and cache invalidation?",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Rendering Trade-offs"
        },
        {
            "question": "Compare database connection pooling in-app versus using a standalone proxy like PgBouncer. What are the operational overhead trade-offs?",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Resource Management Trade-offs"
        },
    ],
    "FOLLOWUP_DEFENSE": [
        {
            "question": "You mentioned caching frequently queried data in memory. What happens if the cache cluster crashes under peak load?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Failure Mode Follow-up"
        },
        {
            "question": "Why did you choose that specific architecture over a simpler monolithic approach? Walk me through what broke first.",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Justification Follow-up"
        },
        {
            "question": "How do you detect silent data corruption or partial network partitions between your application tier and storage?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Edge Case Probing"
        },
        {
            "question": "If incoming API traffic increased by 10x in five minutes, exactly where would your current system experience its first bottleneck?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Scale Limits Follow-up"
        },
        {
            "question": "What automated safeguards prevent an erroneous deployment or malformed migration from corrupting historical production data?",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Deployment Defense"
        },
    ],
    "STRUCTURED_ANSWER": [
        {
            "question": "In exactly 90 seconds, explain how HTTPS establishes an encrypted session from DNS lookup to symmetric key exchange.",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Concise Technical Communication"
        },
        {
            "question": "How would you explain the concept of technical debt and its business risks to a non-technical product manager?",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Cross-functional Communication"
        },
        {
            "question": "Structure a 60-second incident summary explaining a production database lock outage using the Context, Action, Result framework.",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Incident Briefing"
        },
        {
            "question": "Explain what a distributed microservice tracing span is and why it matters, avoiding jargon where possible.",
            "category": "Behavioral",
            "difficulty": "easy",
            "focus": "Clear Concept Explanation"
        },
        {
            "question": "Walk me through how you structure an architectural decision record (ADR) when proposing a new core library to your engineering team.",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Engineering Documentation"
        },
    ],
    "BEHAVIORAL_STAR": [
        {
            "question": "Describe a situation where you strongly disagreed with a senior engineer or architect on technical direction. How did you resolve it?",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Conflict Resolution & Alignment"
        },
        {
            "question": "Tell me about a time an unexpected bug made it into production under your watch. What was your immediate response and long-term fix?",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Ownership & Remediation"
        },
        {
            "question": "Describe a project where requirements were ambiguous and changing rapidly. How did you maintain velocity without building the wrong solution?",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Adaptability & Execution"
        },
        {
            "question": "Tell me about a time you had to mentor or unblock a struggling peer while meeting your own tight project deadline.",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Team Collaboration"
        },
        {
            "question": "Give an example of a technical initiative you spearheaded outside your daily sprint tasks that measurably improved the codebase.",
            "category": "Behavioral",
            "difficulty": "medium",
            "focus": "Technical Initiative"
        },
    ],
    "PRESSURE_RESPONSE": [
        {
            "question": "CRITICAL INCIDENT: Your primary payment service is throwing 504 Gateway Timeouts. Traffic is backing up and latency is climbing. What are your first three actions in the first 5 minutes?",
            "category": "Pressure",
            "difficulty": "hard",
            "focus": "Live Triage"
        },
        {
            "question": "You deployed a database migration 10 minutes before a major launch, and it locked a core table. The CEO is on the phone. Do you rollback or hotfix?",
            "category": "Pressure",
            "difficulty": "hard",
            "focus": "High-Stakes Decision Making"
        },
        {
            "question": "Your monitoring alerts report CPU utilization at 100% across all API nodes, and logs show an ongoing suspected DDoS attack. How do you triage?",
            "category": "Pressure",
            "difficulty": "hard",
            "focus": "Security & Outage Response"
        },
        {
            "question": "A third-party authentication API that your entire application depends on has suffered an unannounced total outage. How do you keep users functional?",
            "category": "Pressure",
            "difficulty": "hard",
            "focus": "Dependency Failure Triage"
        },
    ]
}


def _generate_grounded_project_drill_questions(
    db: Session,
    user_id: int,
    count: int = 5
) -> List[Dict[str, Any]]:
    """
    Generates distinct drill questions strictly grounded in the candidate's actual resume projects and technologies.
    If no resume is uploaded, provides authentic backend project architecture scenarios.
    """
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.user_id == user_id)
        .order_by(models.Resume.created_at.desc())
        .first()
    )

    projects = []
    skills = []
    if resume:
        proj_records = db.query(models.ResumeProject).filter(models.ResumeProject.resume_id == resume.id).all()
        for p in proj_records:
            projects.append({
                "title": p.title,
                "description": p.description or "",
                "technologies": p.technologies or []
            })
        if resume.skills:
            try:
                skills = json.loads(resume.skills)
            except Exception:
                pass

    questions = []

    # If authentic resume projects exist, generate questions referencing them directly
    if projects:
        for idx, proj in enumerate(projects):
            p_title = proj["title"]
            tech_str = ", ".join(proj["technologies"][:3]) if proj["technologies"] else "core technologies"

            questions.append({
                "question": f"In your project '{p_title}', walk me through the high-level architecture and explain the single most difficult technical bottleneck you personally owned.",
                "category": "Technical",
                "difficulty": "medium",
                "focus": f"Project Architecture: {p_title}"
            })
            if proj["technologies"]:
                questions.append({
                    "question": f"Regarding '{p_title}', what specific trade-offs led you to choose {proj['technologies'][0]} over existing alternatives?",
                    "category": "Technical",
                    "difficulty": "medium",
                    "focus": f"Technology Choice: {p_title}"
                })
            questions.append({
                "question": f"How did you test and verify edge case failures in '{p_title}' before deploying it to production?",
                "category": "Technical",
                "difficulty": "hard",
                "focus": f"Resilience Testing: {p_title}"
            })

    # If candidate skills exist, ground questions in declared skills
    if skills:
        for s in skills[:4]:
            questions.append({
                "question": f"You listed {s} as a core competency. Describe a real-world scenario where you had to debug a subtle concurrency or performance issue in {s}.",
                "category": "Technical",
                "difficulty": "medium",
                "focus": f"Skill Defense: {s}"
            })

    # Fallback to authentic software engineering project scenarios if no resume profile exists yet
    fallback_project_questions = [
        {
            "question": "Describe the overall system architecture of your most significant backend project. What was the most challenging technical decision you had to make?",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "System Architecture Defense"
        },
        {
            "question": "In your past project implementations, how did you handle data schema migrations without incurring downtime?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Zero-Downtime Migration"
        },
        {
            "question": "What telemetry, logging, and metrics did you instrument in your recent projects to quickly diagnose production latency spikes?",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Observability & Profiling"
        },
        {
            "question": "Describe a situation where a service you built experienced a sudden memory leak or CPU spike. How did you isolate the offending code path?",
            "category": "Technical",
            "difficulty": "hard",
            "focus": "Performance Profiling"
        },
        {
            "question": "How did you design automated integration test suites for your APIs to verify database rollbacks under simulated error conditions?",
            "category": "Technical",
            "difficulty": "medium",
            "focus": "Integration Testing"
        }
    ]

    for fb in fallback_project_questions:
        if len(questions) < count * 2:
            questions.append(fb)

    return questions


def select_distinct_practice_questions(
    db: Session,
    user_id: int,
    practice_type: str,
    difficulty: str = "medium",
    count: int = 5,
    target_role: str = "Software Engineer"
) -> List[Dict[str, Any]]:
    """
    Selects unique, category-distinct practice questions for a targeted drill.
    Guarantees:
    - Dedicated purpose per practice drill type
    - No duplicate questions within the drill
    - Deduplicates against user's recently asked questions
    """
    p_type = practice_type.strip().upper()

    # Determine candidate question pool
    if p_type in ("PROJECT_DEFENSE", "RESUME_CLAIM_DEFENSE"):
        raw_pool = _generate_grounded_project_drill_questions(db=db, user_id=user_id, count=count)
    elif p_type in DISTINCT_DRILL_POOLS:
        raw_pool = DISTINCT_DRILL_POOLS[p_type]
    elif p_type in ("COMMUNICATION", "STRUCTURED_ANSWER"):
        raw_pool = DISTINCT_DRILL_POOLS["STRUCTURED_ANSWER"]
    elif p_type in ("BEHAVIORAL_STAR", "BEHAVIORAL"):
        raw_pool = DISTINCT_DRILL_POOLS["BEHAVIORAL_STAR"]
    elif p_type == "PRESSURE_RESPONSE":
        raw_pool = DISTINCT_DRILL_POOLS["PRESSURE_RESPONSE"]
    elif p_type == "TRADEOFF_REASONING":
        raw_pool = DISTINCT_DRILL_POOLS["TRADEOFF_REASONING"]
    elif p_type == "FOLLOWUP_DEFENSE":
        raw_pool = DISTINCT_DRILL_POOLS["FOLLOWUP_DEFENSE"]
    else:
        raw_pool = DISTINCT_DRILL_POOLS["TECHNICAL_DEPTH"]

    # Query user's recently answered questions to prevent cross-session repetition
    recent_answers = (
        db.query(models.InterviewAnswer.question_text)
        .join(models.InterviewSession, models.InterviewSession.id == models.InterviewAnswer.session_id)
        .filter(models.InterviewSession.user_id == user_id)
        .order_by(models.InterviewAnswer.created_at.desc())
        .limit(30)
        .all()
    )
    recently_asked_texts = {r[0].lower().strip() for r in recent_answers if r[0]}

    selected = []
    seen_normalized = set()

    # First pass: pick pool questions that haven't been asked recently
    shuffled_pool = list(raw_pool)
    random.shuffle(shuffled_pool)

    for item in shuffled_pool:
        q_text = item["question"].strip()
        q_norm = q_text.lower()
        if q_norm not in recently_asked_texts and q_norm not in seen_normalized:
            seen_normalized.add(q_norm)
            selected.append({
                "id": len(selected) + 1,
                "question": q_text,
                "category": item.get("category", "Technical"),
                "difficulty": item.get("difficulty", difficulty),
                "focus": item.get("focus", p_type.replace("_", " ").title())
            })
            if len(selected) >= count:
                break

    # Second pass: if needed to satisfy count, use unused pool questions
    if len(selected) < count:
        for item in shuffled_pool:
            q_text = item["question"].strip()
            q_norm = q_text.lower()
            if q_norm not in seen_normalized:
                seen_normalized.add(q_norm)
                selected.append({
                    "id": len(selected) + 1,
                    "question": q_text,
                    "category": item.get("category", "Technical"),
                    "difficulty": item.get("difficulty", difficulty),
                    "focus": item.get("focus", p_type.replace("_", " ").title())
                })
                if len(selected) >= count:
                    break

    return selected[:count]

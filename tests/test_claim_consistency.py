"""
tests/test_claim_consistency.py
Automated tests for Per-claim Resume Consistency and Dynamic Session Consistency Scoring.

Verifies:
- Labels: consistent, weak_support, low_consistency, insufficient_evidence
- Minimum turns guard (< 2 turns -> insufficient_evidence)
- Exact observable wording on low_consistency:
  "Low consistency between this resume claim and the answers given; this is a verification-risk indicator, not a finding of dishonesty."
- Session-level consistency derivation and consistency_source ('claim_level' vs 'legacy')
- Golden ordering: strong candidate score > weak candidate score
"""

import pytest
import backend.models as models
from backend.services.claim_consistency_service import evaluate_session_claim_consistency


def test_insufficient_evidence_guard_single_turn(client, db_session, test_user):
    """A claim with only 1 answered turn must receive insufficient_evidence, never judged from 1 answer."""
    # 1. Create resume with claim
    resume = models.Resume(
        user_id=test_user.id,
        filename="test_guard.pdf",
        raw_text="Test resume text",
        skills='["test"]',
        resume_score=80.0
    )
    db_session.add(resume)
    db_session.flush()

    claim = models.ResumeClaim(
        resume_id=resume.id,
        claim_text="Built a high-performance Redis caching layer with FastAPI reducing query latency by 85%.",
        claim_type="project",
        technologies=["redis", "fastapi"],
        has_metric=True,
        probe_priority=0.8
    )
    db_session.add(claim)
    db_session.flush()

    # 2. Create session and ask 1 question on this claim
    session = models.InterviewSession(
        user_id=test_user.id,
        resume_id=resume.id,
        mode="technical",
        difficulty="medium",
        total_questions=3,
        status="in_progress"
    )
    db_session.add(session)
    db_session.flush()

    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text="How did you structure the Redis caching tier in FastAPI?",
        question_type="probe",
        source="resume_claim",
        claim_id=claim.id,
        ladder_stage="T1_FOUNDATION"
    )
    db_session.add(q1)
    db_session.flush()

    ans1 = models.InterviewAnswer(
        session_id=session.id,
        question_id=q1.id,
        question_text=q1.question_text,
        transcript="I set up a Redis connection pool in FastAPI and cached user sessions."
    )
    db_session.add(ans1)
    db_session.flush()

    ev1 = models.AnswerEvaluation(
        answer_id=ans1.id,
        overall_score=85.0,
        technical_score=85.0,
        verification_risk_score=15.0,
        verification_risk_level="low"
    )
    db_session.add(ev1)
    db_session.commit()

    # 3. Evaluate claim consistency
    res = evaluate_session_claim_consistency(session.id, db_session)
    assert res["consistency_source"] == "legacy"
    assert len(res["claim_records"]) == 1
    c_rec = res["claim_records"][0]
    assert c_rec["label"] == "insufficient_evidence"
    assert c_rec["answers_considered"] == 1
    assert "minimum 2 required" in c_rec["evidence"][0]


def test_consistent_claim_two_strong_turns(client, db_session, test_user):
    """When a claim is probed across 2+ turns with strong technical specifics, label is 'consistent'."""
    resume = models.Resume(
        user_id=test_user.id,
        filename="test_strong.pdf",
        raw_text="PostgreSQL database query tuning with composite B-tree indexes.",
        skills='["postgresql", "sql"]',
        resume_score=85.0
    )
    db_session.add(resume)
    db_session.flush()

    claim = models.ResumeClaim(
        resume_id=resume.id,
        claim_text="Optimized PostgreSQL queries on 10M rows using composite B-tree indexing.",
        claim_type="project",
        technologies=["postgresql", "sql"],
        has_metric=True,
        probe_priority=0.85
    )
    db_session.add(claim)
    db_session.flush()

    session = models.InterviewSession(
        user_id=test_user.id,
        resume_id=resume.id,
        mode="technical",
        difficulty="medium",
        total_questions=2,
        status="in_progress"
    )
    db_session.add(session)
    db_session.flush()

    # Turn 1
    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text="How did you diagnose the slow queries in PostgreSQL?",
        question_type="probe",
        source="resume_claim",
        claim_id=claim.id,
        ladder_stage="T1_FOUNDATION"
    )
    db_session.add(q1)
    db_session.flush()

    ans1 = models.InterviewAnswer(
        session_id=session.id,
        question_id=q1.id,
        question_text=q1.question_text,
        transcript="I used EXPLAIN ANALYZE in PostgreSQL to identify sequential table scans over 10M records."
    )
    db_session.add(ans1)
    db_session.flush()

    ev1 = models.AnswerEvaluation(
        answer_id=ans1.id,
        overall_score=85.0,
        technical_score=85.0,
        verification_risk_score=10.0,
        verification_risk_level="low"
    )
    db_session.add(ev1)

    # Turn 2
    q2 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=2,
        question_text="What architectural trade-offs did you consider when indexing in PostgreSQL?",
        question_type="probe",
        source="resume_claim",
        claim_id=claim.id,
        ladder_stage="T2_TRADE_OFFS"
    )
    db_session.add(q2)
    db_session.flush()

    ans2 = models.InterviewAnswer(
        session_id=session.id,
        question_id=q2.id,
        question_text=q2.question_text,
        transcript="We evaluated composite B-tree vs hash indexing in PostgreSQL, balancing write amplification against read latency."
    )
    db_session.add(ans2)
    db_session.flush()

    ev2 = models.AnswerEvaluation(
        answer_id=ans2.id,
        overall_score=88.0,
        technical_score=88.0,
        verification_risk_score=12.0,
        verification_risk_level="low"
    )
    db_session.add(ev2)
    db_session.commit()

    res = evaluate_session_claim_consistency(session.id, db_session)
    assert res["consistency_source"] == "claim_level"
    assert len(res["claim_records"]) == 1
    c_rec = res["claim_records"][0]
    assert c_rec["label"] == "consistent"
    assert c_rec["answers_considered"] == 2
    assert res["derived_score"] >= 80.0


def test_low_consistency_exact_wording(client, db_session, test_user):
    """When a claim receives weak answers with elevated risk, label is 'low_consistency' with required wording."""
    resume = models.Resume(
        user_id=test_user.id,
        filename="test_weak.pdf",
        raw_text="Led Kubernetes migration and infrastructure automation.",
        skills='["kubernetes", "docker"]',
        resume_score=75.0
    )
    db_session.add(resume)
    db_session.flush()

    claim = models.ResumeClaim(
        resume_id=resume.id,
        claim_text="Led Kubernetes migration across 40 microservices with zero downtime.",
        claim_type="project",
        technologies=["kubernetes", "docker"],
        has_metric=True,
        probe_priority=0.9
    )
    db_session.add(claim)
    db_session.flush()

    session = models.InterviewSession(
        user_id=test_user.id,
        resume_id=resume.id,
        mode="technical",
        difficulty="medium",
        total_questions=2,
        status="in_progress"
    )
    db_session.add(session)
    db_session.flush()

    # Turn 1: vague
    q1 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=1,
        question_text="How did you configure the Kubernetes migration?",
        question_type="probe",
        source="resume_claim",
        claim_id=claim.id,
        ladder_stage="T1_FOUNDATION"
    )
    db_session.add(q1)
    db_session.flush()

    ans1 = models.InterviewAnswer(
        session_id=session.id,
        question_id=q1.id,
        question_text=q1.question_text,
        transcript="We basically just worked on various tasks and someone on the team did the setup."
    )
    db_session.add(ans1)
    db_session.flush()

    ev1 = models.AnswerEvaluation(
        answer_id=ans1.id,
        overall_score=40.0,
        technical_score=40.0,
        verification_risk_score=70.0,
        verification_risk_level="elevated"
    )
    db_session.add(ev1)

    # Turn 2: vague
    q2 = models.InterviewQuestion(
        session_id=session.id,
        sequence_order=2,
        question_text="What challenges occurred during the migration?",
        question_type="probe",
        source="resume_claim",
        claim_id=claim.id,
        ladder_stage="T2_TRADE_OFFS"
    )
    db_session.add(q2)
    db_session.flush()

    ans2 = models.InterviewAnswer(
        session_id=session.id,
        question_id=q2.id,
        question_text=q2.question_text,
        transcript="There were different things that happened but we streamlined the process using best practices."
    )
    db_session.add(ans2)
    db_session.flush()

    ev2 = models.AnswerEvaluation(
        answer_id=ans2.id,
        overall_score=42.0,
        technical_score=42.0,
        verification_risk_score=68.0,
        verification_risk_level="elevated"
    )
    db_session.add(ev2)
    db_session.commit()

    res = evaluate_session_claim_consistency(session.id, db_session)
    assert res["consistency_source"] == "claim_level"
    c_rec = res["claim_records"][0]
    assert c_rec["label"] == "low_consistency"

    # Verify exact required wording
    expected_wording = "Low consistency between this resume claim and the answers given; this is a verification-risk indicator, not a finding of dishonesty."
    assert any(expected_wording in ev_str for ev_str in c_rec["evidence"])


def test_golden_ordering_strong_vs_weak_candidate(client, db_session, test_user):
    """Prove that for identical claims, strong candidate consistency score > weak candidate consistency score."""
    resume = models.Resume(
        user_id=test_user.id,
        filename="golden_comp.pdf",
        raw_text="Kafka distributed event streaming.",
        skills='["kafka", "python"]',
        resume_score=80.0
    )
    db_session.add(resume)
    db_session.flush()

    claim = models.ResumeClaim(
        resume_id=resume.id,
        claim_text="Engineered a high-throughput Kafka streaming pipeline handling 50k events/sec.",
        claim_type="project",
        technologies=["kafka"],
        has_metric=True,
        probe_priority=0.9
    )
    db_session.add(claim)
    db_session.flush()

    # Session A: Strong Candidate
    s_a = models.InterviewSession(user_id=test_user.id, resume_id=resume.id, total_questions=2)
    db_session.add(s_a)
    db_session.flush()

    for i in range(2):
        q = models.InterviewQuestion(session_id=s_a.id, sequence_order=i+1, question_text=f"Q{i}", claim_id=claim.id)
        db_session.add(q)
        db_session.flush()
        ans = models.InterviewAnswer(session_id=s_a.id, question_id=q.id, transcript="Kafka partition rebalancing.")
        db_session.add(ans)
        db_session.flush()
        ev = models.AnswerEvaluation(answer_id=ans.id, overall_score=88.0, verification_risk_score=10.0)
        db_session.add(ev)

    # Session B: Weak Candidate
    s_b = models.InterviewSession(user_id=test_user.id, resume_id=resume.id, total_questions=2)
    db_session.add(s_b)
    db_session.flush()

    for i in range(2):
        q = models.InterviewQuestion(session_id=s_b.id, sequence_order=i+1, question_text=f"Q{i}", claim_id=claim.id)
        db_session.add(q)
        db_session.flush()
        ans = models.InterviewAnswer(session_id=s_b.id, question_id=q.id, transcript="We basically just ran it.")
        db_session.add(ans)
        db_session.flush()
        ev = models.AnswerEvaluation(answer_id=ans.id, overall_score=40.0, verification_risk_score=75.0)
        db_session.add(ev)

    db_session.commit()

    res_a = evaluate_session_claim_consistency(s_a.id, db_session)
    res_b = evaluate_session_claim_consistency(s_b.id, db_session)

    assert res_a["derived_score"] > res_b["derived_score"], (
        f"Ordering failed: Strong candidate ({res_a['derived_score']}) <= Weak candidate ({res_b['derived_score']})"
    )
    assert res_a["claim_records"][0]["label"] == "consistent"
    assert res_b["claim_records"][0]["label"] == "low_consistency"

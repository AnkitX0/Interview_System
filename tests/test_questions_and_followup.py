import pytest
from backend.services.question_selector import select_questions
from backend.services.followup_generator import generate_followup


def test_select_questions_by_mode_and_difficulty(db_session):
    """Test filtering questions by technical mode and difficulty."""
    questions = select_questions(
        db=db_session,
        mode="technical",
        difficulty="medium",
        count=2
    )
    assert len(questions) == 2
    for q in questions:
        assert q["category"] == "Technical"


def test_select_questions_prioritizes_resume_skills(db_session):
    """Candidate with Docker skill should receive Docker question when available."""
    questions = select_questions(
        db=db_session,
        mode="technical",
        difficulty="medium",
        count=3,
        resume_skills=["Docker"]
    )
    assert len(questions) > 0
    # At least one question should reference Docker
    question_texts = [q["question"].lower() for q in questions]
    assert any("docker" in qt for qt in question_texts)


def test_followup_generator_rules():
    """Verify follow-up probing triggers based on answer gaps."""
    # 1. Very short answer -> request elaboration
    fu_short = generate_followup(
        question="Explain REST architecture.",
        answer="It is an API architectural style."
    )
    assert "elaborate" in fu_short.lower() or "detail" in fu_short.lower()

    # 2. Substantial answer without metrics (> 25 words) -> probe for metrics
    fu_no_metrics = generate_followup(
        question="Describe a challenge you faced.",
        answer="We designed a distributed microservice to process incoming orders because the previous monolithic architecture was slow and difficult to maintain. We rewrote the database queries and significantly improved overall system architecture."
    )
    assert "quantify" in fu_no_metrics.lower() or "impact" in fu_no_metrics.lower()

    # 3. Answer with metrics but no tradeoff words (> 25 words) -> probe for tradeoffs
    fu_no_tradeoffs = generate_followup(
        question="Describe a challenge you faced.",
        answer="In our production system, we deployed Redis caching to speed up requests and cache database queries, resulting in a 50% decrease in response latency across all backend services."
    )
    assert "tradeoff" in fu_no_tradeoffs.lower() or "alternative" in fu_no_tradeoffs.lower()

    # 4. Answer about team conflict with metrics & tradeoffs -> probe for communication
    fu_conflict = generate_followup(
        question="Describe a disagreement with a teammate.",
        answer="In our team, we evaluated architectural tradeoffs between PostgreSQL and MongoDB for 500k daily users. I disagreed with my team lead regarding document nesting, and we resolved the conflict through benchmarking."
    )
    assert "communication" in fu_conflict.lower() or "stakeholder" in fu_conflict.lower()


# ===========================================================================
# PHASE 3: ADAPTIVE PROBE LADDER & DECISION POLICY TESTS
# ===========================================================================

def test_adaptive_probe_ladder_and_next_flow(client, golden_answers):
    """
    Test adaptive /interview/{session_id}/next flow:
    1. Upload resume with high-priority claim.
    2. Start interview linked to resume.
    3. Call /next -> policy initiates PROBE_CLAIM on T1_FOUNDATION.
    4. Submit strong answer.
    5. Call /next -> policy advances to T2_TRADE_OFFS.
    6. Verify interview_decisions rows logged with reasons and inputs.
    """
    # 1. Upload resume
    res = client.post(
        "/resume/upload",
        data={
            "raw_text": """
            Alex Turner
            EXPERIENCE
            - Architected distributed event stream processing with Kafka and Redis serving 40,000 requests per second.
            - Reduced database p99 latency by 50% using PostgreSQL connection pooling.
            SKILLS
            Python, Kafka, Redis, PostgreSQL, Docker
            """
        }
    )
    assert res.status_code == 200
    resume_id = res.json()["id"]

    # 2. Start session with resume
    start_res = client.post(
        "/interview/start",
        json={
            "mode": "technical",
            "difficulty": "medium",
            "number_of_questions": 3,
            "resume_id": resume_id,
            "target_role": "Backend Engineer"
        }
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    # 3. Call /next for dynamic question
    next_res_1 = client.post(f"/interview/{session_id}/next")
    assert next_res_1.status_code == 200
    n1 = next_res_1.json()
    assert n1["done"] is False
    assert n1["question"]["source"] == "resume_claim"
    assert n1["question"]["ladder_stage"] == "T1_FOUNDATION"
    assert "PROBE_CLAIM" in n1["decision"]["decision"]

    # 4. Submit answer to T1
    client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": n1["question"]["id"],
            "question_text": n1["question"]["question"],
            "transcript": golden_answers["strong"],
            "response_time": 25.0,
        }
    )

    # 5. Call /next again -> advances to T2_TRADE_OFFS
    next_res_2 = client.post(f"/interview/{session_id}/next")
    assert next_res_2.status_code == 200
    n2 = next_res_2.json()
    assert n2["done"] is False
    assert n2["question"]["ladder_stage"] == "T2_TRADE_OFFS"
    assert n2["decision"]["decision"] == "ADVANCE_LADDER"
    assert "T2_TRADE_OFFS" in n2["decision"]["reason"]

    # 6. Submit answer to T2
    client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": n2["question"]["id"],
            "question_text": n2["question"]["question"],
            "transcript": golden_answers["strong"],
            "response_time": 30.0,
        }
    )

    # 7. Call /next -> advances to T3_INCIDENT
    next_res_3 = client.post(f"/interview/{session_id}/next")
    assert next_res_3.status_code == 200
    n3 = next_res_3.json()
    assert n3["done"] is False
    assert n3["question"]["ladder_stage"] == "T3_INCIDENT"
    assert n3["decision"]["decision"] == "ADVANCE_LADDER"

    # 8. Submit 3rd answer (reaching total_questions = 3)
    client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": n3["question"]["id"],
            "question_text": n3["question"]["question"],
            "transcript": golden_answers["strong"],
            "response_time": 20.0,
        }
    )

    # 9. Calling /next when total questions answered -> returns done: True
    next_res_final = client.post(f"/interview/{session_id}/next")
    assert next_res_final.status_code == 200
    assert next_res_final.json()["done"] is True
    assert next_res_final.json()["decision"]["decision"] == "COMPLETE_SESSION"

    # 10. Verify caption on probe question
    assert n1["question"]["caption"] is not None
    assert "Follow-up on:" in n1["question"]["caption"]

    # 11. Complete interview and verify report contains decision_log and question metadata
    client.post(f"/interview/{session_id}/complete")
    rep_res = client.get(f"/report/{session_id}")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert "decision_log" in rep_data
    assert len(rep_data["decision_log"]) >= 4
    dec_types = [d["decision"] for d in rep_data["decision_log"]]
    assert "START_SESSION" in dec_types
    assert "PROBE_CLAIM" in dec_types
    assert "ADVANCE_LADDER" in dec_types
    assert "COMPLETE_SESSION" in dec_types

    # Ensure answers have generated_reason attached
    assert len(rep_data["answers"]) == 3
    assert rep_data["answers"][0]["generated_reason"] is not None



def test_difficulty_stepping_logic():
    """Verify calculate_adjusted_difficulty steps up on strong scores and steps down on weak."""
    from backend.services.adaptive_engine import calculate_adjusted_difficulty
    import backend.models as models

    # 1. High scores >= 80 -> step up
    ev_strong = [
        models.AnswerEvaluation(overall_score=85.0),
        models.AnswerEvaluation(overall_score=88.0),
    ]
    assert calculate_adjusted_difficulty(ev_strong, "easy") == "medium"
    assert calculate_adjusted_difficulty(ev_strong, "medium") == "hard"
    assert calculate_adjusted_difficulty(ev_strong, "hard") == "hard"  # ceiling

    # 2. Low scores < 60 -> step down
    ev_weak = [
        models.AnswerEvaluation(overall_score=50.0),
        models.AnswerEvaluation(overall_score=45.0),
    ]
    assert calculate_adjusted_difficulty(ev_weak, "hard") == "medium"
    assert calculate_adjusted_difficulty(ev_weak, "medium") == "easy"
    assert calculate_adjusted_difficulty(ev_weak, "easy") == "easy"  # floor

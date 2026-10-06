import json
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import get_db
import backend.models as models
from backend.services.auth_service import hash_password, create_access_token
from backend.services.weakness_diagnosis_engine import diagnose_session_weaknesses
from backend.services.recurring_weakness_service import aggregate_user_weaknesses, get_recurring_weaknesses
from backend.services.velocity_service import calculate_improvement_velocity
from backend.services.readiness_engine import compute_longitudinal_readiness
from backend.services.practice_recommendation_engine import select_next_practice


def test_phase4_export_includes_practice_recommendations(client: TestClient, db_session: Session, test_user: models.User):
    """
    Verifies that GET /auth/export includes the practice_recommendations table.
    """
    # Create a session and practice recommendation for test_user
    session = models.InterviewSession(
        user_id=test_user.id,
        mode="technical",
        difficulty="medium",
        target_role="Software Engineer",
        status="completed"
    )
    db_session.add(session)
    db_session.flush()

    rec = models.PracticeRecommendation(
        user_id=test_user.id,
        source_session_id=session.id,
        weakness_type="VAGUE_TECHNICAL_EXPLANATION",
        dimension="technical",
        priority=1,
        rationale="Needs deeper technical precision.",
        practice_type="TECHNICAL_DEPTH",
        target_count=5,
        difficulty="medium",
        status="pending",
        decision_metadata={"source": "test"}
    )
    db_session.add(rec)
    db_session.commit()

    res = client.get("/auth/export")
    assert res.status_code == 200
    data = res.json()
    assert "practice_recommendations" in data
    assert len(data["practice_recommendations"]) >= 1
    found = [r for r in data["practice_recommendations"] if r["weakness_type"] == "VAGUE_TECHNICAL_EXPLANATION"]
    assert len(found) == 1
    assert found[0]["practice_type"] == "TECHNICAL_DEPTH"
    assert found[0]["source_session_id"] == session.id


def test_phase4_cascading_deletion_leaves_zero_orphan_recommendations(client: TestClient, db_session: Session):
    """
    Verifies that deleting an interview session cleans up session-linked recommendations,
    and deleting a user account cascades to delete all user practice recommendations.
    """
    user = models.User(
        email="cascade_user@example.com",
        password_hash=hash_password("password123"),
        full_name="Cascade Test User"
    )
    db_session.add(user)
    db_session.flush()

    session1 = models.InterviewSession(
        user_id=user.id,
        mode="technical",
        difficulty="medium",
        status="completed"
    )
    session2 = models.InterviewSession(
        user_id=user.id,
        mode="behavioral",
        difficulty="medium",
        status="completed"
    )
    db_session.add_all([session1, session2])
    db_session.flush()

    rec1 = models.PracticeRecommendation(
        user_id=user.id,
        source_session_id=session1.id,
        weakness_type="VAGUE_TECHNICAL_EXPLANATION",
        dimension="technical",
        priority=1,
        rationale="Rationale 1",
        practice_type="TECHNICAL_DEPTH",
        target_count=5,
        status="pending"
    )
    rec2 = models.PracticeRecommendation(
        user_id=user.id,
        source_session_id=session2.id,
        weakness_type="POOR_STAR_STRUCTURE",
        dimension="behavioral",
        priority=1,
        rationale="Rationale 2",
        practice_type="STRUCTURED_ANSWER",
        target_count=5,
        status="pending"
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Delete session 1 via DELETE /interview/{session_id}
    del_res = client.delete(f"/interview/{session1.id}", headers=headers)
    assert del_res.status_code == 200

    # Verify rec1 was cleaned up because session1 was deleted
    orphan_session1_recs = db_session.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.source_session_id == session1.id
    ).count()
    assert orphan_session1_recs == 0

    # Rec2 still exists for session 2
    rec2_count = db_session.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.source_session_id == session2.id
    ).count()
    assert rec2_count == 1

    # 2. Delete user account via DELETE /auth/account
    acct_del = client.request("DELETE", "/auth/account", json={"password": "password123"}, headers=headers)
    assert acct_del.status_code == 200

    # Verify 0 orphan rows left in practice_recommendations for this user
    remaining_recs = db_session.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.user_id == user.id
    ).count()
    assert remaining_recs == 0


def test_phase4_cross_user_isolation(client: TestClient, client_b: TestClient, db_session: Session, test_user: models.User):
    """
    Ensures User B cannot view User A's recommendations or readiness metrics.
    """
    # Create recommendation for User A (test_user)
    rec_a = models.PracticeRecommendation(
        user_id=test_user.id,
        weakness_type="PRESSURE_ANXIETY",
        dimension="delivery",
        priority=1,
        rationale="Private recommendation for user A",
        practice_type="PRESSURE_RESPONSE",
        target_count=3,
        status="pending"
    )
    db_session.add(rec_a)
    db_session.commit()

    # User B requests recommendations via client_b
    res_b = client_b.get("/practice/recommendations")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert all(r.get("user_id") != test_user.id for r in data_b)
    assert not any(r["weakness_type"] == "PRESSURE_ANXIETY" for r in data_b)

    # User B requests readiness via client_b
    res_readiness_b = client_b.get("/readiness/current")
    assert res_readiness_b.status_code == 200
    assert res_readiness_b.json()["status"] == "no_data"
    assert res_readiness_b.json()["current_readiness"] is None


def test_golden_persona_improving_trajectory(db_session: Session):
    """
    Persona 1: Candidate steadily improving across 4 comparable sessions (60 -> 70 -> 80 -> 85).
    Verifies positive velocity and higher readiness score.
    """
    user = models.User(
        email="improving_cand@example.com",
        password_hash=hash_password("pass123"),
        full_name="Improving Candidate"
    )
    db_session.add(user)
    db_session.flush()

    scores = [60.0, 70.0, 80.0, 85.0]
    for idx, s in enumerate(scores):
        session = models.InterviewSession(
            user_id=user.id,
            mode="technical",
            difficulty="medium",
            target_role="Software Engineer",
            status="completed",
            total_questions=2,
            current_question_index=2
        )
        db_session.add(session)
        db_session.flush()

        # Add 2 answers per session to satisfy comparability requirements
        for q_idx in range(1, 3):
            ans = models.InterviewAnswer(
                session_id=session.id,
                question_id=q_idx,
                question_text=f"Sample Question {q_idx}",
                transcript="Detailed implementation with metrics.",
                duration_seconds=30.0,
                wpm=120.0
            )
            db_session.add(ans)
        db_session.flush()

        score_rec = models.SessionScore(
            session_id=session.id,
            communication_score=s,
            technical_score=s,
            behavioral_score=s,
            resume_consistency_score=s,
            readiness_score=s,
            strongest_category="Technical",
            weakest_category="Communication",
            insights=json.dumps([])
        )
        db_session.add(score_rec)
    db_session.commit()

    vel = calculate_improvement_velocity(user.id, db_session)
    assert vel["status"] == "computed"
    assert vel["velocity_per_session"] > 0
    assert vel["readiness_delta"] == 25.0

    readiness = compute_longitudinal_readiness(user.id, db_session)
    assert readiness["current_readiness"] >= 75.0
    assert readiness["comparable_sessions_count"] == 4
    assert readiness["trend"] == "improving"


def test_golden_persona_declining_trajectory(db_session: Session):
    """
    Persona 2: Candidate with declining scores across 3 comparable sessions (85 -> 75 -> 65).
    Verifies negative velocity.
    """
    user = models.User(
        email="declining_cand@example.com",
        password_hash=hash_password("pass123"),
        full_name="Declining Candidate"
    )
    db_session.add(user)
    db_session.flush()

    scores = [85.0, 75.0, 65.0]
    for s in scores:
        session = models.InterviewSession(
            user_id=user.id,
            mode="technical",
            difficulty="medium",
            target_role="Software Engineer",
            status="completed",
            total_questions=2,
            current_question_index=2
        )
        db_session.add(session)
        db_session.flush()

        # Add 2 answers per session to satisfy comparability requirements
        for q_idx in range(1, 3):
            ans = models.InterviewAnswer(
                session_id=session.id,
                question_id=q_idx,
                question_text=f"Sample Question {q_idx}",
                transcript="Sample answer text.",
                duration_seconds=30.0,
                wpm=120.0
            )
            db_session.add(ans)
        db_session.flush()

        score_rec = models.SessionScore(
            session_id=session.id,
            communication_score=s,
            technical_score=s,
            behavioral_score=s,
            resume_consistency_score=s,
            readiness_score=s,
            strongest_category="Technical",
            weakest_category="Communication",
            insights=json.dumps([])
        )
        db_session.add(score_rec)
    db_session.commit()

    vel = calculate_improvement_velocity(user.id, db_session)
    assert vel["status"] == "computed"
    assert vel["velocity_per_session"] < 0
    assert vel["readiness_delta"] == -20.0


def test_golden_persona_weak_communication(db_session: Session):
    """
    Persona 3: Candidate with weak communication signals (excessive verbal fillers and long pauses).
    Verifies weakness diagnosis flags communication gap.
    """
    user = models.User(
        email="weak_comm@example.com",
        password_hash=hash_password("pass123"),
        full_name="Weak Comm Candidate"
    )
    db_session.add(user)
    db_session.flush()

    session = models.InterviewSession(
        user_id=user.id,
        mode="behavioral",
        difficulty="medium",
        target_role="Software Engineer",
        status="completed"
    )
    db_session.add(session)
    db_session.flush()

    ans1 = models.InterviewAnswer(
        session_id=session.id,
        question_id=1,
        question_text="Tell me about a conflict at work.",
        transcript="Um, basically, like, I had a conflict, you know, with the design, like, totally.",
        duration_seconds=25.0,
        wpm=60.0
    )
    ans2 = models.InterviewAnswer(
        session_id=session.id,
        question_id=2,
        question_text="Describe your biggest challenge.",
        transcript="Well, um, basically, like, it was, you know, hard to fix the bug, like, really.",
        duration_seconds=28.0,
        wpm=62.0
    )
    db_session.add_all([ans1, ans2])
    db_session.flush()

    vm1 = models.VoiceMetrics(
        answer_id=ans1.id,
        words_per_minute=60.0,
        filler_word_count=6,
        longest_pause=4.0,
        speech_source="speech"
    )
    vm2 = models.VoiceMetrics(
        answer_id=ans2.id,
        words_per_minute=62.0,
        filler_word_count=5,
        longest_pause=3.8,
        speech_source="speech"
    )
    db_session.add_all([vm1, vm2])
    db_session.commit()

    weaknesses = diagnose_session_weaknesses(session.id, db_session)
    assert len(weaknesses) >= 1
    dimensions = [w["dimension"] for w in weaknesses]
    assert "communication" in dimensions


def test_end_to_end_practice_learning_loop(client: TestClient, db_session: Session, test_user: models.User):
    """
    Persona 4 & Learning Loop:
    1. Diagnose weakness in Session 1
    2. Practice Recommendation Engine generates drill
    3. Candidate launches targeted practice session via /practice/start
    4. Candidate answers and completes drill via /practice/{id}/complete
    5. Recommendation marked completed
    """
    # Session 1: Baseline with diagnosed gap
    session1 = models.InterviewSession(
        user_id=test_user.id,
        mode="technical",
        difficulty="medium",
        target_role="Software Engineer",
        status="completed"
    )
    db_session.add(session1)
    db_session.flush()

    ans = models.InterviewAnswer(
        session_id=session1.id,
        question_id=1,
        question_text="Explain database indexing.",
        transcript="Indexes make things faster using trees.",
        duration_seconds=15.0,
        wpm=80.0
    )
    db_session.add(ans)
    db_session.flush()

    ev = models.AnswerEvaluation(
        answer_id=ans.id,
        structure_score=55.0,
        technical_score=50.0,
        reasoning_score=52.0,
        overall_score=52.0,
        engine_used="rubric"
    )
    db_session.add(ev)
    db_session.commit()

    # Select next practice and save to DB
    recs = select_next_practice(test_user.id, db_session, source_session_id=session1.id, save_to_db=True)
    assert len(recs) > 0
    rec = recs[0]
    rec_id = rec["id"]

    # Candidate starts practice via client
    start_res = client.post("/practice/start", json={
        "practice_type": rec["practice_type"],
        "recommendation_id": rec_id,
        "question_count": 3,
        "difficulty": "medium"
    })
    assert start_res.status_code == 200
    practice_data = start_res.json()
    practice_session_id = practice_data["session_id"]
    assert practice_data["practice_type"] == rec["practice_type"]

    # Complete practice drill
    comp_res = client.post(f"/practice/{practice_session_id}/complete")
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "completed"

    # Verify recommendation updated to completed
    updated_rec = db_session.query(models.PracticeRecommendation).filter(
        models.PracticeRecommendation.id == rec_id
    ).first()
    assert updated_rec.status == "completed"
    assert updated_rec.completed_at is not None

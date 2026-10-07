import pytest
from backend.models import models


def test_start_practice_invalid_type_rejected(client):
    res = client.post("/practice/start", json={"practice_type": "INVALID_TYPE"})
    assert res.status_code == 400
    msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "Invalid practice_type" in msg


def test_start_practice_technical_depth_success(client, db_session, test_user):
    payload = {
        "practice_type": "TECHNICAL_DEPTH",
        "target_role": "Backend Engineer",
        "difficulty": "medium",
        "question_count": 3
    }
    res = client.post("/practice/start", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["practice_type"] == "TECHNICAL_DEPTH"
    assert data["time_limit_seconds"] == 90
    assert data["mode"] == "technical"
    assert len(data["questions"]) > 0

    session_id = data["session_id"]
    sess_db = db_session.query(models.InterviewSession).filter_by(id=session_id).first()
    assert sess_db is not None
    assert sess_db.user_id == test_user.id
    assert sess_db.status == "in_progress"


def test_start_practice_pressure_response_sets_45s_limit(client):
    payload = {
        "practice_type": "PRESSURE_RESPONSE",
        "target_role": "Backend Engineer",
        "difficulty": "hard",
        "question_count": 3
    }
    res = client.post("/practice/start", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["time_limit_seconds"] == 45
    assert data["mode"] == "pressure"


def test_complete_practice_generates_before_after_comparison(client, db_session, test_user):
    # Prior baseline session: Technical depth = 64
    s_prior = models.InterviewSession(
        user_id=test_user.id,
        target_role="Backend Engineer",
        mode="technical",
        difficulty="medium",
        status="completed"
    )
    db_session.add(s_prior)
    db_session.flush()

    a1 = models.InterviewAnswer(session_id=s_prior.id, transcript="Prior answer 1")
    a2 = models.InterviewAnswer(session_id=s_prior.id, transcript="Prior answer 2")
    db_session.add_all([a1, a2])
    sc_prior = models.SessionScore(
        session_id=s_prior.id,
        readiness_score=64.0,
        technical_score=64.0,
        communication_score=70.0
    )
    db_session.add(sc_prior)

    # Active practice recommendation: Technical depth
    rec = models.PracticeRecommendation(
        user_id=test_user.id,
        source_session_id=s_prior.id,
        weakness_type="tech_shallow_depth",
        dimension="technical",
        practice_type="TECHNICAL_DEPTH",
        priority=1,
        rationale="Improve technical reasoning.",
        status="in_progress"
    )
    db_session.add(rec)
    db_session.commit()

    # Current practice session: Technical depth = 72
    s_curr = models.InterviewSession(
        user_id=test_user.id,
        target_role="Backend Engineer",
        mode="technical",
        difficulty="medium",
        status="in_progress"
    )
    db_session.add(s_curr)
    db_session.flush()

    a3 = models.InterviewAnswer(session_id=s_curr.id, transcript="Practice answer 1")
    a4 = models.InterviewAnswer(session_id=s_curr.id, transcript="Practice answer 2")
    db_session.add_all([a3, a4])
    sc_curr = models.SessionScore(
        session_id=s_curr.id,
        readiness_score=72.0,
        technical_score=72.0,
        communication_score=70.0
    )
    db_session.add(sc_curr)
    db_session.commit()

    res = client.post(f"/practice/{s_curr.id}/complete")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"

    comparison = data["comparison"]
    assert comparison["has_comparable_baseline"] is True
    assert comparison["dimension"] == "Technical Depth"
    assert comparison["before_score"] == 64.0
    assert comparison["after_score"] == 72.0
    assert comparison["delta"] == 8.0
    assert "+8.0 points" in comparison["summary"]

    # Verify recommendation updated to completed
    db_session.refresh(rec)
    assert rec.status == "completed"
    assert rec.completed_at is not None


def test_cross_user_isolation_on_practice_endpoints(client, client_b, db_session, test_user):
    # Session belonging to user test_user
    s_user_a = models.InterviewSession(user_id=test_user.id, status="in_progress")
    db_session.add(s_user_a)
    db_session.commit()

    # User B tries to complete User A's session -> 404
    res = client_b.post(f"/practice/{s_user_a.id}/complete")
    assert res.status_code == 404
    msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "not found" in msg.lower()


def test_get_recommendations_endpoint(client, test_user):
    res = client.get("/practice/recommendations")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "practice_type" in data[0]
    assert "priority" in data[0]

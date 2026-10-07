import pytest
from backend.models import models


def test_readiness_routes_unauthenticated_returns_401(unauth_client):
    assert unauth_client.get("/readiness/current").status_code == 401
    assert unauth_client.get("/readiness/history").status_code == 401
    assert unauth_client.get("/readiness/forecast").status_code == 401


def test_readiness_current_no_sessions(client, test_user):
    res = client.get("/readiness/current")
    assert res.status_code == 200
    data = res.json()
    assert data["confidence"] == "insufficient_data"
    assert "No completed interview sessions" in data["message"]
    assert "guarantee" in data["disclaimer"].lower()


def test_readiness_routes_with_multiple_sessions(client, db_session, test_user):
    # Add 3 completed sessions for test_user
    scores_vals = [55.0, 63.0, 70.0]
    for idx, sc_val in enumerate(scores_vals):
        s = models.InterviewSession(
            user_id=test_user.id,
            target_role="Backend Engineer",
            mode="technical",
            difficulty="medium",
            status="completed"
        )
        db_session.add(s)
        db_session.flush()

        a1 = models.InterviewAnswer(session_id=s.id, transcript="Ans 1")
        a2 = models.InterviewAnswer(session_id=s.id, transcript="Ans 2")
        db_session.add_all([a1, a2])

        sc = models.SessionScore(
            session_id=s.id,
            readiness_score=sc_val,
            technical_score=sc_val,
            communication_score=sc_val,
            behavioral_score=75.0,
            resume_consistency_score=75.0
        )
        db_session.add(sc)
    db_session.commit()

    # 1. Test /readiness/current
    res_curr = client.get("/readiness/current?target_threshold=80.0")
    assert res_curr.status_code == 200
    data_curr = res_curr.json()
    assert data_curr["status"] == "computed"
    assert data_curr["trend"] == "improving"
    assert data_curr["confidence"] in ("low", "medium")
    assert data_curr["target"]["threshold"] == 80.0
    assert data_curr["target"]["status"] == "in_progress"
    assert data_curr["projection"]["is_meaningful"] is True
    assert data_curr["projection"]["type"] == "Baseline projection"

    # 2. Test /readiness/history
    res_hist = client.get("/readiness/history")
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert data_hist["total_count"] == 3
    assert data_hist["comparable_to_latest_count"] == 3
    assert len(data_hist["sessions"]) == 3

    # 3. Test /readiness/forecast
    res_fc = client.get("/readiness/forecast?target_threshold=80.0")
    assert res_fc.status_code == 200
    data_fc = res_fc.json()
    assert data_fc["trend"] == "improving"
    assert data_fc["projection"]["type"] == "Baseline projection"


def test_noisy_data_caps_confidence(db_session, test_user):
    from backend.services.readiness_engine import calculate_readiness_confidence

    # 8 sessions but wildly noisy scores (standard deviation > 12)
    noisy_scores = [40.0, 85.0, 42.0, 90.0, 38.0, 95.0, 45.0, 92.0]
    conf = calculate_readiness_confidence(len(noisy_scores), noisy_scores, delivery_measured_ratio=1.0)
    # Variance check prevents 'high' rating when scores are erratic
    assert conf == "medium"

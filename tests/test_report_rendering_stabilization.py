import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
import backend.models as models
from backend.services.auth_service import create_access_token, hash_password
from backend.services.scoring_engine import calculate_session_score

@pytest.fixture
def auth_client():
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == "test_report_user@example.com").first()
    if not user:
        user = models.User(
            email="test_report_user@example.com",
            password_hash=hash_password("TestPassword123!"),
            full_name="Report Test User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    token = create_access_token(user_id=user.id)
    client = TestClient(app)
    client.cookies.set("auth_token", token)
    return client, user.id, db

def test_report_endpoint_valid_session(auth_client):
    client, user_id, db = auth_client

    # Create session
    sess = models.InterviewSession(
        user_id=user_id,
        mode="technical",
        difficulty="medium",
        target_role="Backend Engineer",
        status="completed"
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    # Create score record
    score = models.SessionScore(
        session_id=sess.id,
        communication_score=75.0,
        technical_score=80.0,
        behavioral_score=None,
        resume_consistency_score=70.0,
        readiness_score=75.6,
        strongest_category="Technical Depth",
        weakest_category="Resume Consistency",
        insights='["Strong technical foundations.", "Provide more concrete metrics in project defense."]'
    )
    db.add(score)
    db.commit()

    res = client.get(f"/report/{sess.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sess.id
    assert data["readiness_score"] == 75.6
    assert data["subscores"]["technical"] == 80.0
    assert data["subscores"]["communication"] == 75.0
    assert data["delivery_measured"] is False
    assert data["subscores"]["delivery"] is None

def test_report_endpoint_unauthorized(auth_client):
    client, _, _ = auth_client
    # Unauthenticated client
    anon_client = TestClient(app)
    res = anon_client.get("/report/1")
    assert res.status_code == 401

def test_report_endpoint_not_found(auth_client):
    client, _, _ = auth_client
    res = client.get("/report/999999")
    assert res.status_code == 404

def test_readiness_normalization_camera_off():
    # Verify readiness calculation when camera was off (delivery_score = None)
    result = calculate_session_score(
        answer_scores=[80.0, 80.0],
        delivery_score=None,
        technical_scores=[80.0, 80.0],
        communication_scores=[80.0, 80.0],
        consistency_scores=[80.0, 80.0]
    )
    assert result["delivery_measured"] is False
    assert result["delivery_score"] is None
    assert result["final_readiness_score"] == 80.0
    assert result["weights_used"]["delivery"] == 0.0
    assert result["weights_used"]["communication"] == 0.375

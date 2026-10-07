import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db
import backend.models as models
from backend.services.auth_service import hash_password, create_access_token


def test_consent_endpoints_flow(client):
    # 1. Initially empty consent
    res = client.get("/consent")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 2. Grant camera and microphone consent
    grant_res = client.post(
        "/consent",
        json={
            "consent_type": "camera_mic_processing",
            "granted": True,
            "policy_version": "v1.0"
        }
    )
    assert grant_res.status_code == 200
    assert grant_res.json()["consent"]["granted"] is True
    assert grant_res.json()["consent"]["consent_type"] == "camera_mic_processing"

    # 3. Withdraw consent
    revoke_res = client.post(
        "/consent",
        json={
            "consent_type": "camera_mic_processing",
            "granted": False,
            "policy_version": "v1.0"
        }
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["consent"]["granted"] is False

    # 4. Check list has both historical logs
    list_res = client.get("/consent")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 2


def test_resume_deletion_and_isolation(client, client_b):
    # 1. User A creates resume
    upload_res = client.post(
        "/resume/upload",
        data={"raw_text": "Experienced Python Engineer. Skills: Python, FastAPI, Docker. Education: B.Tech CS."}
    )
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["id"]

    # 2. User B attempts to delete User A's resume -> 404
    del_b = client_b.delete(f"/resume/{resume_id}")
    assert del_b.status_code == 404

    # 3. User A deletes their resume -> 200
    del_a = client.delete(f"/resume/{resume_id}")
    assert del_a.status_code == 200

    # 4. Confirm resume is gone
    get_res = client.get(f"/resume/{resume_id}")
    assert get_res.status_code == 404


def test_export_and_account_deletion_flow(db_session):
    # Create isolated user for complete cascading deletion test
    user = models.User(
        email="delete_me@example.com",
        password_hash=hash_password("deletePass1234"),
        full_name="To Be Deleted"
    )
    db_session.add(user)
    db_session.flush()

    profile = models.UserProfile(user_id=user.id, target_role="DevOps Engineer")
    consent = models.ConsentRecord(user_id=user.id, consent_type="camera_mic_processing", granted=True, policy_version="v1.0")
    resume = models.Resume(
        user_id=user.id,
        filename="cv.txt",
        raw_text="Kubernetes expert",
        skills='["Kubernetes", "AWS"]'
    )
    session = models.InterviewSession(user_id=user.id, mode="technical", target_role="DevOps Engineer")
    db_session.add_all([profile, consent, resume, session])
    db_session.flush()

    answer = models.InterviewAnswer(session_id=session.id, question_id=1, transcript="I set up EKS clusters.")
    score = models.SessionScore(session_id=session.id, readiness_score=85.0)
    db_session.add_all([answer, score])
    db_session.flush()

    evaluation = models.AnswerEvaluation(answer_id=answer.id, overall_score=85.0)
    voice = models.VoiceMetrics(answer_id=answer.id, words_per_minute=130.0, speech_source="speech")
    db_session.add_all([evaluation, voice])
    db_session.commit()

    token = create_access_token(user.id)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"

        # 1. Test data export
        export_res = test_client.get("/auth/export")
        assert export_res.status_code == 200
        export_data = export_res.json()
        assert export_data["user"]["email"] == "delete_me@example.com"
        assert export_data["profile"]["target_role"] == "DevOps Engineer"
        assert len(export_data["resumes"]) == 1
        assert len(export_data["interview_sessions"]) == 1
        assert export_data["interview_sessions"][0]["answers"][0]["voice_metrics"]["words_per_minute"] == 130.0
        assert export_data["data_retention_policy"] == "Your data is kept until you delete it."

        # 2. Attempt account deletion with incorrect password -> 401
        wrong_del = test_client.request(
            "DELETE",
            "/auth/account",
            json={"password": "wrongPassword123"}
        )
        assert wrong_del.status_code == 401

        # Confirm user and data still exist
        assert db_session.query(models.User).filter(models.User.id == user.id).first() is not None

        # 3. Delete account with correct password -> 200
        del_res = test_client.request(
            "DELETE",
            "/auth/account",
            json={"password": "deletePass1234"}
        )
        assert del_res.status_code == 200
        assert "permanently deleted" in del_res.json()["message"]

        # 4. Verify full cascading deletion of all associated child rows
        assert db_session.query(models.User).filter(models.User.id == user.id).first() is None
        assert db_session.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first() is None
        assert db_session.query(models.ConsentRecord).filter(models.ConsentRecord.user_id == user.id).count() == 0
        assert db_session.query(models.Resume).filter(models.Resume.user_id == user.id).count() == 0
        assert db_session.query(models.InterviewSession).filter(models.InterviewSession.user_id == user.id).count() == 0
        assert db_session.query(models.InterviewAnswer).filter(models.InterviewAnswer.id == answer.id).first() is None
        assert db_session.query(models.AnswerEvaluation).filter(models.AnswerEvaluation.id == evaluation.id).first() is None
        assert db_session.query(models.VoiceMetrics).filter(models.VoiceMetrics.id == voice.id).first() is None
        assert db_session.query(models.SessionScore).filter(models.SessionScore.id == score.id).first() is None

    app.dependency_overrides.clear()

"""
tests/test_security_question_recovery.py
Comprehensive test suite for security question selection, answer hashing,
attempt limits, case-insensitive normalization, and password recovery.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.auth_service import (
    _rate_limits,
    hash_password,
    verify_password,
    hash_security_answer,
    verify_security_answer,
    normalize_security_answer,
    ALLOWED_SECURITY_QUESTIONS,
)
from backend.config import AUTH_COOKIE_NAME
import backend.models as models


@pytest.fixture(autouse=True)
def clean_rate_limits():
    _rate_limits.clear()
    yield
    _rate_limits.clear()


# ==============================================================================
# 1. Normalization & Hashing Unit Tests
# ==============================================================================

def test_security_answer_normalization():
    assert normalize_security_answer("  The Matrix   ") == "the matrix"
    assert normalize_security_answer("THE   MATRIX") == "the matrix"
    assert normalize_security_answer("the matrix") == "the matrix"
    assert normalize_security_answer("") == ""
    assert normalize_security_answer(None) == ""


def test_security_answer_hashing_and_case_insensitivity():
    answer = "Interstellar"
    hashed = hash_security_answer(answer)

    assert "Interstellar" not in hashed
    assert "interstellar" not in hashed

    # Matching with different case and whitespace
    assert verify_security_answer("interstellar", hashed) is True
    assert verify_security_answer("  INTERSTELLAR  ", hashed) is True
    assert verify_security_answer("Interstellar", hashed) is True

    # Non-matching
    assert verify_security_answer("Inception", hashed) is False
    assert verify_security_answer("", hashed) is False


# ==============================================================================
# 2. Registration with Security Questions
# ==============================================================================

def test_registration_with_security_question_success(client: TestClient, db_session):
    email = "sec.user@gmail.com"
    pwd = "SecUserPass123!"
    q = ALLOWED_SECURITY_QUESTIONS[0]
    ans = "Pulp Fiction"

    res = client.post("/auth/register", json={
        "email": email,
        "password": pwd,
        "full_name": "Security User",
        "security_question": q,
        "security_answer": ans,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["verification_required"] is False
    assert AUTH_COOKIE_NAME in res.cookies

    # Check database persistence
    user = db_session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    assert user.security_question == q
    assert user.security_answer_hash is not None
    assert verify_security_answer("pulp fiction", user.security_answer_hash) is True
    assert user.recovery_attempts == 0


def test_registration_missing_answer_rejected(client: TestClient):
    res = client.post("/auth/register", json={
        "email": "noanswer@gmail.com",
        "password": "Password123!",
        "full_name": "No Answer",
        "security_question": ALLOWED_SECURITY_QUESTIONS[1],
        "security_answer": "",
    })
    assert res.status_code == 400
    assert "enter your answer" in res.json()["error"]["message"].lower()


# ==============================================================================
# 3. Security Question Recovery Flow End-to-End
# ==============================================================================

def test_security_question_recovery_success(client: TestClient, db_session):
    email = "recover.me@gmail.com"
    old_pwd = "OldPassword123!"
    new_pwd = "BrandNewPass123!"
    q = "What was the name of your first pet?"
    ans = "Barnaby"

    # Register user
    client.post("/auth/register", json={
        "email": email,
        "password": old_pwd,
        "full_name": "Pet Owner",
        "security_question": q,
        "security_answer": ans,
    })
    client.cookies.clear()

    # Step 1: Challenge -> Fetch security question
    res_chal = client.post("/auth/recovery/challenge", json={"email": email})
    assert res_chal.status_code == 200
    assert res_chal.json()["question"] == q
    assert res_chal.json()["email"] == email

    # Step 2: Verify answer (case-insensitive with whitespace)
    res_ans = client.post("/auth/recovery/verify-answer", json={
        "email": email,
        "answer": "  BARNABY  ",
    })
    assert res_ans.status_code == 200
    data_ans = res_ans.json()
    assert "recovery_token" in data_ans
    recovery_token = data_ans["recovery_token"]

    # Step 3: Reset password with recovery token
    res_reset = client.post("/auth/recovery/reset-password", json={
        "email": email,
        "recovery_token": recovery_token,
        "new_password": new_pwd,
    })
    assert res_reset.status_code == 200
    assert res_reset.json()["success"] is True

    # Step 4: Token cannot be reused
    res_reuse = client.post("/auth/recovery/reset-password", json={
        "email": email,
        "recovery_token": recovery_token,
        "new_password": "AnotherPassword123!",
    })
    assert res_reuse.status_code == 400

    # Step 5: Old password fails, new password succeeds
    res_old = client.post("/auth/login", json={"email": email, "password": old_pwd})
    assert res_old.status_code == 401

    res_new = client.post("/auth/login", json={"email": email, "password": new_pwd})
    assert res_new.status_code == 200
    assert AUTH_COOKIE_NAME in res_new.cookies


def test_recovery_incorrect_answer_increments_attempts_and_locks_out(client: TestClient, db_session):
    email = "lockout.test@gmail.com"
    q = "What is your favorite movie?"
    ans = "Gladiator"

    client.post("/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Lockout User",
        "security_question": q,
        "security_answer": ans,
    })

    # 4 incorrect answers
    for i in range(1, 5):
        _rate_limits.clear()
        res = client.post("/auth/recovery/verify-answer", json={
            "email": email,
            "answer": f"WrongAnswer{i}",
        })
        assert res.status_code == 400
        msg = res.json()["error"]["message"]
        assert "incorrect security answer" in msg.lower()
        assert f"{5 - i} attempt" in msg.lower()

    # 5th incorrect attempt triggers lockout (HTTP 429)
    _rate_limits.clear()
    res_lockout = client.post("/auth/recovery/verify-answer", json={
        "email": email,
        "answer": "WrongAnswer5",
    })
    assert res_lockout.status_code == 429
    assert "maximum recovery attempts exceeded" in res_lockout.json()["error"]["message"].lower()

    # Subsequent attempt even with correct answer is locked out
    _rate_limits.clear()
    res_locked = client.post("/auth/recovery/verify-answer", json={
        "email": email,
        "answer": ans,
    })
    assert res_locked.status_code == 429


def test_recovery_challenge_nonexistent_email_rejected(client: TestClient):
    res = client.post("/auth/recovery/challenge", json={
        "email": "does.not.exist@gmail.com"
    })
    assert res.status_code == 404
    assert "no account found" in res.json()["error"]["message"].lower()


def test_recovery_weak_password_rejected(client: TestClient):
    email = "weak.pwd@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Weak Pwd User",
        "security_question": ALLOWED_SECURITY_QUESTIONS[0],
        "security_answer": "ValidAnswer",
    })

    # Verify answer to get token
    res_ans = client.post("/auth/recovery/verify-answer", json={
        "email": email,
        "answer": "ValidAnswer",
    })
    token = res_ans.json()["recovery_token"]

    # Attempt to reset with weak password (too short)
    res_weak = client.post("/auth/recovery/reset-password", json={
        "email": email,
        "recovery_token": token,
        "new_password": "short",
    })
    assert res_weak.status_code in (400, 422)


def test_existing_interview_data_preserved_after_password_recovery(client: TestClient, db_session):
    email = "interview.data.preserved@gmail.com"
    old_pwd = "OldPassword123!"
    new_pwd = "NewPassword123!"

    # 1. Register and login
    res_reg = client.post("/auth/register", json={
        "email": email,
        "password": old_pwd,
        "full_name": "Data Candidate",
        "security_question": ALLOWED_SECURITY_QUESTIONS[2],
        "security_answer": "Sparky",
    })
    user_id = res_reg.json()["user"]["id"]

    # 2. Create an interview session
    session = models.InterviewSession(
        user_id=user_id,
        session_policy="STANDARD",
        status="ACTIVE",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    session_id = session.id

    # 3. Recover and change password
    client.cookies.clear()
    res_ans = client.post("/auth/recovery/verify-answer", json={
        "email": email,
        "answer": "sparky",
    })
    token = res_ans.json()["recovery_token"]

    client.post("/auth/recovery/reset-password", json={
        "email": email,
        "recovery_token": token,
        "new_password": new_pwd,
    })

    # 4. Sign in with new password
    res_login = client.post("/auth/login", json={"email": email, "password": new_pwd})
    assert res_login.status_code == 200

    # 5. Verify the historical interview session still belongs to the user and is intact
    saved_session = db_session.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id,
        models.InterviewSession.user_id == user_id
    ).first()
    assert saved_session is not None
    assert saved_session.status == "ACTIVE"

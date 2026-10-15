"""
tests/test_production_auth_e2e.py
End-to-end verification of production authentication hardening:
- Registration without mandatory email verification
- Immediate login upon registration
- Login with valid credentials
- Rejection of invalid credentials without user enumeration
- Logout and session clearance
- Protected route authorization
- Cross-user data isolation
"""

import pytest
from fastapi.testclient import TestClient
from backend.config import AUTH_COOKIE_NAME
from backend.services.auth_service import _rate_limits


@pytest.fixture(autouse=True)
def clear_limits():
    _rate_limits.clear()
    yield
    _rate_limits.clear()


def test_registration_and_immediate_login(client: TestClient):
    email = "demo.candidate@gmail.com"
    pwd = "DemoCandidate123!"

    # 1. Register new user with cookie-only auth
    client.cookies.clear()
    client.headers.pop("Authorization", None)
    res_reg = client.post("/auth/register", json={
        "email": email,
        "password": pwd,
        "full_name": "Demo Candidate",
    })
    assert res_reg.status_code == 200
    data_reg = res_reg.json()

    # Confirms optional email verification is honored
    assert data_reg["verification_required"] is False
    assert data_reg["email_status"] == "VERIFICATION_DISABLED"
    assert data_reg["user"]["email"] == email

    # Immediate session cookie is set
    assert AUTH_COOKIE_NAME in res_reg.cookies

    # 2. Access protected endpoint immediately
    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == email

    # 3. Log out
    res_logout = client.post("/auth/logout")
    assert res_logout.status_code == 200

    # 4. Protected endpoint now returns 401
    res_unauth = client.get("/auth/me")
    assert res_unauth.status_code == 401

    # 5. Invalid credentials return 401 with generic error
    res_bad = client.post("/auth/login", json={
        "email": email,
        "password": "WrongPassword999!",
    })
    assert res_bad.status_code == 401
    assert "invalid email or password" in res_bad.json()["error"]["message"].lower()

    # Non-existent email also returns generic 401 (no user enumeration)
    res_nonexistent = client.post("/auth/login", json={
        "email": "nonexistent.user@gmail.com",
        "password": "AnyPassword123!",
    })
    assert res_nonexistent.status_code == 401
    assert "invalid email or password" in res_nonexistent.json()["error"]["message"].lower()

    # 6. Log back in with valid credentials
    res_login = client.post("/auth/login", json={
        "email": email,
        "password": pwd,
    })
    assert res_login.status_code == 200
    assert AUTH_COOKIE_NAME in res_login.cookies
    assert res_login.json()["user"]["email"] == email


def test_cross_user_isolation(client: TestClient):
    # User A
    client.cookies.clear()
    client.headers.pop("Authorization", None)
    user_a_email = "candidate.alice@gmail.com"
    res_a = client.post("/auth/register", json={
        "email": user_a_email,
        "password": "AlicePassword123!",
        "full_name": "Alice Candidate",
    })
    assert res_a.status_code == 200

    # Alice uploads a resume
    alice_resume = client.post(
        "/resume/upload",
        data={"raw_text": "Alice Software Engineer Resume with Python, FastAPI, and PostgreSQL experience."}
    )
    assert alice_resume.status_code == 200
    alice_resume_id = alice_resume.json()["id"]

    # User B
    client.cookies.clear()
    client.headers.pop("Authorization", None)
    user_b_email = "candidate.bob@gmail.com"
    res_b = client.post("/auth/register", json={
        "email": user_b_email,
        "password": "BobPassword123!",
        "full_name": "Bob Candidate",
    })
    assert res_b.status_code == 200

    # Bob tries to access Alice's resume -> 404 Not Found (User isolation)
    res_bob_access = client.get(f"/resume/{alice_resume_id}")
    assert res_bob_access.status_code == 404
    assert "not found" in res_bob_access.json()["error"]["message"].lower()

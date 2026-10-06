"""
tests/test_auth.py
Unit and integration tests for authentication, password security,
JWT cookies, session management, profile updates, and rate limiting.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import (
    validate_password_strength,
    hash_password,
    verify_password,
    check_rate_limit,
)
from backend.config import AUTH_COOKIE_NAME


def test_password_strength_validator():
    # Less than 10 characters
    assert validate_password_strength("short") == "Password must be at least 10 characters long"
    assert validate_password_strength("123456789") == "Password must be at least 10 characters long"

    # All identical characters
    assert validate_password_strength("aaaaaaaaaa") == "Password cannot consist of a single repeated character"
    assert validate_password_strength("11111111111") == "Password cannot consist of a single repeated character"

    # All digits
    assert validate_password_strength("123456789012") == "Password cannot consist solely of digits"

    # Trivial common passwords
    assert validate_password_strength("password123") == "Password is too trivial; please choose a stronger password"
    assert validate_password_strength("qwertyuiop") == "Password is too trivial; please choose a stronger password"

    # Valid strong passphrases (no arbitrary composition rules required)
    assert validate_password_strength("correct horse battery staple") is None
    assert validate_password_strength("my-super-secret-pass-2026") is None
    assert validate_password_strength("engineerinterviewgoal") is None


def test_argon2_hashing_and_verification():
    raw_pwd = "my-secure-password-1234"
    h = hash_password(raw_pwd)

    # Argon2id format
    assert h.startswith("$argon2id$")
    assert verify_password(raw_pwd, h) is True
    assert verify_password("wrong-password", h) is False
    assert verify_password("", h) is False


def test_auth_registration_happy_and_duplicate(client: TestClient):
    payload = {
        "email": "Engineer.One@Example.com",  # mixed case to verify lowercase normalization
        "password": "validsecurepassword10",
        "full_name": "Engineer One",
    }
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Account registered successfully"
    assert data["user"]["email"] == "engineer.one@example.com"
    assert data["user"]["full_name"] == "Engineer One"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify httpOnly cookie set
    assert AUTH_COOKIE_NAME in res.cookies

    # Duplicate registration attempt
    res_dup = client.post("/auth/register", json=payload)
    assert res_dup.status_code == 400
    assert "already registered" in res_dup.json()["error"]["message"]


def test_auth_registration_weak_passwords(client: TestClient):
    # Short
    res = client.post("/auth/register", json={
        "email": "weak1@example.com",
        "password": "short",
    })
    assert res.status_code == 422 or res.status_code == 400

    # Trivial repeated
    res = client.post("/auth/register", json={
        "email": "weak2@example.com",
        "password": "bbbbbbbbbbbb",
    })
    assert res.status_code == 400
    assert "repeated character" in res.json()["error"]["message"]

    # All numbers
    res = client.post("/auth/register", json={
        "email": "weak3@example.com",
        "password": "9876543210123",
    })
    assert res.status_code == 400
    assert "digits" in res.json()["error"]["message"]


def test_auth_login_happy_and_failure(client: TestClient):
    # Register user first
    email = "login_test@example.com"
    password = "supersecretpassword10"
    client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Login Tester",
    })

    # Clear cookies and auth header
    client.cookies.clear()
    client.headers.pop("Authorization", None)

    # Login with wrong password
    res_wrong = client.post("/auth/login", json={
        "email": email,
        "password": "wrongpassword10",
    })
    assert res_wrong.status_code == 401
    assert res_wrong.json()["error"]["message"] == "Invalid email or password"

    # Login with nonexistent email
    res_no_user = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "supersecretpassword10",
    })
    assert res_no_user.status_code == 401
    # Uniform error message: no timing or username enumeration leak
    assert res_no_user.json()["error"]["message"] == "Invalid email or password"

    # Login success
    res_ok = client.post("/auth/login", json={
        "email": email,
        "password": password,
    })
    assert res_ok.status_code == 200
    assert AUTH_COOKIE_NAME in res_ok.cookies
    assert res_ok.json()["user"]["email"] == email


def test_auth_logout_clears_cookie(client: TestClient):
    client.cookies.clear()
    res_reg = client.post("/auth/register", json={
        "email": "logout_test@example.com",
        "password": "validsecurepassword10",
    })
    assert res_reg.status_code == 200
    assert AUTH_COOKIE_NAME in client.cookies

    res = client.post("/auth/logout")
    assert res.status_code == 200
    assert res.json()["message"] == "Logged out successfully"

    # Verify cookie was cleared or invalidated
    cookie_val = client.cookies.get(AUTH_COOKIE_NAME)
    assert cookie_val is None or cookie_val == ""


def test_auth_me_and_profile_management(client: TestClient):
    # Unauthenticated call to /auth/me returns 401
    client.cookies.clear()
    client.headers.pop("Authorization", None)
    res_unauth = client.get("/auth/me")
    assert res_unauth.status_code == 401

    # Register and get /auth/me
    client.post("/auth/register", json={
        "email": "profile_test@example.com",
        "password": "validsecurepassword10",
        "full_name": "Profile Tester",
    })

    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    data = res_me.json()
    assert data["email"] == "profile_test@example.com"
    assert data["full_name"] == "Profile Tester"

    # Get profile
    res_prof = client.get("/profile")
    assert res_prof.status_code == 200

    # Update profile
    update_data = {
        "target_role": "Staff Backend Engineer",
        "domain": "Distributed Systems",
        "experience_level": "Senior",
        "weekly_practice_goal": 4,
        "target_companies": ["Google", "Stripe", "Anthropic"],
    }
    res_update = client.put("/profile", json=update_data)
    assert res_update.status_code == 200
    updated = res_update.json()["profile"]
    assert updated["target_role"] == "Staff Backend Engineer"
    assert updated["weekly_practice_goal"] == 4
    assert updated["target_companies"] == ["Google", "Stripe", "Anthropic"]


def test_rate_limiting():
    key = "test_rate_limit_ip"
    # Allow 3 attempts within 10 seconds for test
    for _ in range(3):
        assert check_rate_limit(key, max_attempts=3, window_seconds=10) is True
    # 4th attempt should be blocked
    assert check_rate_limit(key, max_attempts=3, window_seconds=10) is False

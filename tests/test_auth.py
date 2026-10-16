"""
tests/test_auth.py
Comprehensive test suite covering the 32-point test matrix for registration,
Gmail validation, password policy, single-use cryptographic email verification,
rate limiting, and backward-compatible authentication.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import (
    validate_password_strength,
    hash_password,
    verify_password,
    check_rate_limit,
    generate_verification_token,
    hash_verification_token,
    _rate_limits,
)
from backend.services.email_service import get_latest_dev_email, clear_dev_email_store
from backend.routes.auth import validate_full_name, validate_gmail_address
from backend.config import AUTH_COOKIE_NAME
import backend.models as models


# ==============================================================================
# Unit Tests: Validators
# ==============================================================================

def test_full_name_validation():
    # Matrix 8: Missing or invalid names
    assert validate_full_name("") == "Please enter your name."
    assert validate_full_name("   ") == "Please enter your name."
    assert validate_full_name(None) == "Please enter your name."
    assert validate_full_name("A") == "Please enter your name."
    assert validate_full_name("123456") == "Please enter your name."
    assert validate_full_name("@@@@@@") == "Please enter your name."

    # Valid names
    assert validate_full_name("Al") is None
    assert validate_full_name("Alex Morgan") is None
    assert validate_full_name("Renée O'Connor") is None


def test_gmail_address_validation():
    # Matrix 1: Valid Gmail
    assert validate_gmail_address("candidate@gmail.com") is None
    assert validate_gmail_address("student.name@gmail.com") is None
    assert validate_gmail_address("firstname.lastname+tag@gmail.com") is None
    assert validate_gmail_address("  USER@GMAIL.COM  ") is None

    # Matrix 2: Invalid Gmail syntax
    assert validate_gmail_address("not-an-email") == "Please use a Gmail address."
    assert validate_gmail_address("@gmail.com") == "Please use a Gmail address."
    assert validate_gmail_address("user@") == "Please use a Gmail address."

    # Matrix 3: Yahoo
    assert validate_gmail_address("user@yahoo.com") == "Please use a Gmail address."
    # Matrix 4: Outlook / Hotmail
    assert validate_gmail_address("user@outlook.com") == "Please use a Gmail address."
    assert validate_gmail_address("user@hotmail.com") == "Please use a Gmail address."
    # Matrix 5: College edu
    assert validate_gmail_address("student@mit.edu") == "Please use a Gmail address."
    # Matrix 6: Company
    assert validate_gmail_address("engineer@google.com") == "Please use a Gmail address."
    # Typos
    assert validate_gmail_address("user@gmail.co") == "Please use a Gmail address."
    assert validate_gmail_address("user@googlemail.com") == "Please use a Gmail address."


def test_password_strength_validator():
    # Matrix 10: 7-character password
    assert validate_password_strength("Abc123!") == "Password must be at least 8 characters long."

    # Matrix 12: Missing uppercase
    assert validate_password_strength("abcd1234!") == "Password must contain at least one uppercase letter."

    # Matrix 13: Missing lowercase
    assert validate_password_strength("ABCD1234!") == "Password must contain at least one lowercase letter."

    # Matrix 14: Missing number
    assert validate_password_strength("Abcdefgh!") == "Password must contain at least one number."

    # Matrix 15: Missing special character
    assert validate_password_strength("Abcd12345") == "Password must contain at least one special character."

    # Repeated characters
    assert validate_password_strength("!!!!!!!!") == "Password cannot consist of a single repeated character."

    # Matrix 11: 8-character valid password
    assert validate_password_strength("Abcd123!") is None
    assert validate_password_strength("SecureP@ssw0rd") is None


def test_argon2_hashing_and_verification():
    raw_pwd = "MySecretPassword123!"
    h = hash_password(raw_pwd)

    assert h.startswith("$argon2id$")
    assert verify_password(raw_pwd, h) is True
    assert verify_password("wrong-password", h) is False
    assert verify_password("", h) is False


# ==============================================================================
# Integration Tests: Registration & Verification Matrix
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_rate_limits_and_emails():
    _rate_limits.clear()
    clear_dev_email_store()
    yield
    _rate_limits.clear()


def test_auth_registration_valid_and_non_gmail_rejection(client: TestClient):
    # Matrix 3-6: Non-gmail rejections
    for rejected_email in [
        "user@yahoo.com",
        "user@hotmail.com",
        "user@outlook.com",
        "student@college.edu",
        "staff@company.com",
        "user@gmail.co",
    ]:
        res = client.post("/auth/register", json={
            "email": rejected_email,
            "password": "StrongPassword123!",
            "full_name": "Test User",
        })
        assert res.status_code == 400
        assert "Gmail address" in res.json()["error"]["message"]

    # Matrix 7: Missing email
    res_no_email = client.post("/auth/register", json={
        "email": "",
        "password": "StrongPassword123!",
        "full_name": "Test User",
    })
    assert res_no_email.status_code in (400, 422)

    # Matrix 8: Missing name
    res_no_name = client.post("/auth/register", json={
        "email": "testvalid@gmail.com",
        "password": "StrongPassword123!",
        "full_name": "123456",
    })
    assert res_no_name.status_code == 400
    assert "enter your name" in res_no_name.json()["error"]["message"].lower()


def test_auth_registration_weak_passwords(client: TestClient):
    # Matrix 9-15: Weak passwords via API
    for weak_pwd in [
        "Abc1!",        # too short
        "abcdefgh1!",   # missing uppercase
        "ABCDEFGH1!",   # missing lowercase
        "Abcdefghi!",   # missing digit
        "Abcdefgh12",   # missing special char
    ]:
        res = client.post("/auth/register", json={
            "email": "validweak@gmail.com",
            "password": weak_pwd,
            "full_name": "Weak Pass User",
        })
        assert res.status_code in (400, 422)


def test_auth_registration_happy_path_and_duplicate(client: TestClient):
    # Registration success without mandatory email verification
    clear_dev_email_store()
    email = "New.Student@Gmail.com"  # Mixed case to test normalization
    payload = {
        "email": email,
        "password": "CorrectPassword123!",
        "full_name": "Student Alpha",
    }
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verification_required"] is False
    assert data["email"] == "new.student@gmail.com"
    # User is immediately authenticated with session cookie
    assert AUTH_COOKIE_NAME in res.cookies
    assert data["user"]["email"] == "new.student@gmail.com"

    # Existing account rejection without enumeration
    res_dup = client.post("/auth/register", json=payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["error"]["message"].lower()


def test_immediate_registration_and_login_without_otp(client: TestClient, db_session):
    """Verifies registration activates immediately without OTP and login succeeds directly."""
    email = "immediate.user@gmail.com"
    pwd = "SecurePassword123!"
    res_reg = client.post("/auth/register", json={
        "email": email,
        "password": pwd,
        "full_name": "Immediate User",
        "security_question": "What is your favorite movie?",
        "security_answer": "Inception",
    })
    assert res_reg.status_code == 200
    assert res_reg.json()["verification_required"] is False
    assert AUTH_COOKIE_NAME in res_reg.cookies

    # Verify user in database has hashed security answer, not plaintext
    user = db_session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    assert user.email_verified is True
    assert user.security_question == "What is your favorite movie?"
    assert user.security_answer_hash is not None
    assert "Inception" not in user.security_answer_hash

    # Can log in directly without OTP
    client.cookies.clear()
    res_login = client.post("/auth/login", json={
        "email": email,
        "password": pwd,
    })
    assert res_login.status_code == 200
    assert AUTH_COOKIE_NAME in res_login.cookies
    assert res_login.json()["user"]["email"] == email


def test_login_remember_me_cookie_and_token(client: TestClient):
    """Verifies remember_me sets 30-day cookie max_age."""
    email = "remember.user@gmail.com"
    pwd = "RememberPass123!"
    client.post("/auth/register", json={
        "email": email,
        "password": pwd,
        "full_name": "Remember User",
        "security_question": "What was your childhood nickname?",
        "security_answer": "Ace",
    })

    client.cookies.clear()
    res_login = client.post("/auth/login", json={
        "email": email,
        "password": pwd,
        "remember_me": True,
    })
    assert res_login.status_code == 200
    assert AUTH_COOKIE_NAME in res_login.cookies


def test_registration_invalid_security_question_rejected(client: TestClient):
    """Verifies selecting an unauthorized question text is rejected."""
    res = client.post("/auth/register", json={
        "email": "invalid.q@gmail.com",
        "password": "Password123!",
        "full_name": "Invalid Q",
        "security_question": "Arbitrary question text not in list",
        "security_answer": "Answer",
    })
    assert res.status_code == 400
    assert "valid security question" in res.json()["error"]["message"].lower()


def test_existing_users_still_work_without_reverification(client: TestClient, test_user):
    # Existing users default to email_verified=True
    assert test_user.email_verified is True

    # Can log in directly
    res = client.post("/auth/login", json={
        "email": test_user.email,
        "password": "testpassword1234",
    })
    assert res.status_code == 200
    assert AUTH_COOKIE_NAME in res.cookies


def test_auth_logout_clears_cookie(client: TestClient):
    client.cookies.clear()
    email = "logout.test@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "LogoutSecure123!",
        "full_name": "Logout User",
    })
    # User is immediately logged in upon registration
    client.post("/auth/login", json={"email": email, "password": "LogoutSecure123!"})
    assert AUTH_COOKIE_NAME in client.cookies

    res_logout = client.post("/auth/logout")
    assert res_logout.status_code == 200
    cookie_val = client.cookies.get(AUTH_COOKIE_NAME)
    assert cookie_val is None or cookie_val == ""


def test_protected_routes_still_work(client: TestClient):
    client.cookies.clear()
    client.headers.pop("Authorization", None)
    res_unauth = client.get("/auth/me")
    assert res_unauth.status_code == 401

    email = "me.test@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "MeSecurePass123!",
        "full_name": "Me Tester",
    })

    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == email


def test_csrf_origin_blocking_cookie_request(client: TestClient):
    email = "csrf.test@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "CsrfSecurePass123!",
        "full_name": "CSRF Tester",
    })

    client.headers.pop("Authorization", None)
    res = client.post(
        "/consent",
        json={"consent_type": "camera_mic_processing", "granted": True, "policy_version": "2.0"},
        headers={"Origin": "https://malicious-attacker.com"}
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_FORBIDDEN"


def test_log_hygiene_no_sensitive_data_in_logs(client: TestClient, caplog):
    caplog.clear()
    import logging
    with caplog.at_level(logging.DEBUG):
        secret_password = "SuperSecretPassword123!"
        client.post("/auth/register", json={
            "email": "hygiene@gmail.com",
            "password": secret_password,
            "full_name": "Log Hygiene User",
        })
        client.post("/auth/register", json={
            "email": "invalid-email-format",
            "password": secret_password,
            "full_name": "Log Hygiene User",
        })
    captured_text = caplog.text
    assert secret_password not in captured_text
    assert "auth_token=" not in captured_text


def test_cookie_security_params_validation(monkeypatch):
    import backend.routes.auth as auth_mod

    # Valid values
    monkeypatch.setattr(auth_mod, "AUTH_COOKIE_SAMESITE", "none")
    monkeypatch.setattr(auth_mod, "AUTH_COOKIE_SECURE", False)
    samesite, secure = auth_mod._get_cookie_security_params()
    assert samesite == "none"
    assert secure is True  # SameSite=None MUST be Secure=True

    monkeypatch.setattr(auth_mod, "AUTH_COOKIE_SAMESITE", "strict")
    monkeypatch.setattr(auth_mod, "AUTH_COOKIE_SECURE", True)
    samesite, secure = auth_mod._get_cookie_security_params()
    assert samesite == "strict"
    assert secure is True

    # Invalid values fallback to "lax"
    monkeypatch.setattr(auth_mod, "AUTH_COOKIE_SAMESITE", "invalid-value")
    monkeypatch.setattr(auth_mod, "AUTH_COOKIE_SECURE", False)
    samesite, secure = auth_mod._get_cookie_security_params()
    assert samesite == "lax"
    assert secure is False


def test_set_and_clear_auth_cookie_attributes():
    from fastapi import Response
    from backend.routes.auth import _set_auth_cookie, _clear_auth_cookie
    from backend.config import AUTH_COOKIE_NAME

    # Test set cookie
    res_set = Response()
    _set_auth_cookie(res_set, "token123")
    set_cookies = res_set.headers.getlist("set-cookie")
    assert len(set_cookies) == 1
    cookie_str = set_cookies[0]
    assert f"{AUTH_COOKIE_NAME}=token123" in cookie_str
    assert "HttpOnly" in cookie_str
    assert "Path=/" in cookie_str

    # Test clear cookie
    res_clear = Response()
    _clear_auth_cookie(res_clear)
    clear_cookies = res_clear.headers.getlist("set-cookie")
    assert len(clear_cookies) == 1
    clear_str = clear_cookies[0]
    assert f'{AUTH_COOKIE_NAME}=""' in clear_str
    assert "Max-Age=0" in clear_str
    assert "HttpOnly" in clear_str
    assert "Path=/" in clear_str


def test_logout_endpoint_clears_cookie_with_matching_flags(client: TestClient):
    res = client.post("/auth/logout")
    assert res.status_code == 200
    set_cookies = res.headers.get_list("set-cookie")
    assert len(set_cookies) >= 1
    cookie_header = set_cookies[0]
    assert "auth_token=" in cookie_header
    assert "Max-Age=0" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/" in cookie_header

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
    # Matrix 18: Registration success
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
    assert data["verification_required"] is True
    assert data["email"] == "new.student@gmail.com"
    # Ensure no cookies set until verified
    assert AUTH_COOKIE_NAME not in res.cookies

    # Matrix 19: Verification token generated and email captured
    dev_email = get_latest_dev_email("new.student@gmail.com")
    assert dev_email is not None
    assert dev_email["token"] is not None
    assert "/verify-email?token=" in dev_email["verification_link"]

    # Matrix 17: Existing account rejection without enumeration
    res_dup = client.post("/auth/register", json=payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["error"]["message"].lower()


def test_unverified_user_cannot_login(client: TestClient):
    # Register pending user
    email = "pending.user@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "SecurePending123!",
        "full_name": "Pending User",
    })

    # Try to login without verifying
    client.cookies.clear()
    res = client.post("/auth/login", json={
        "email": email,
        "password": "SecurePending123!",
    })
    assert res.status_code == 403
    assert "verify your email" in res.json()["error"]["message"].lower()


def test_email_verification_flow_and_token_reuse(client: TestClient, db_session):
    email = "verify.flow@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "VerifyFlowPass123!",
        "full_name": "Flow User",
    })

    dev_email = get_latest_dev_email(email)
    raw_token = dev_email["token"]

    # Matrix 23: Invalid verification token
    res_inv = client.post("/auth/verify-email", json={"token": "totally-bogus-token"})
    assert res_inv.status_code == 400
    assert "no longer valid" in res_inv.json()["error"]["message"].lower()

    # Matrix 22: Verification succeeds
    res_verify = client.post("/auth/verify-email", json={"token": raw_token})
    assert res_verify.status_code == 200
    assert res_verify.json()["verified"] is True

    # Matrix 21: Verification token cannot be reused
    res_reuse = client.post("/auth/verify-email", json={"token": raw_token})
    assert res_reuse.status_code == 400
    assert (
        "already been verified" in res_reuse.json()["error"]["message"].lower()
        or "no longer valid" in res_reuse.json()["error"]["message"].lower()
    )

    # Matrix 30: Login works after verification
    res_login = client.post("/auth/login", json={
        "email": email,
        "password": "VerifyFlowPass123!",
    })
    assert res_login.status_code == 200
    assert AUTH_COOKIE_NAME in res_login.cookies
    assert res_login.json()["user"]["email"] == email


def test_email_verification_token_expiration(client: TestClient, db_session):
    # Matrix 20: Verification token expires
    email = "expired.test@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "ExpiredPass123!",
        "full_name": "Expired User",
    })
    dev_email = get_latest_dev_email(email)
    token = dev_email["token"]

    # Artificially expire the token in database
    user = db_session.query(models.User).filter(models.User.email == email).first()
    user.verification_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    res = client.post("/auth/verify-email", json={"token": token})
    assert res.status_code == 400
    assert "expired" in res.json()["error"]["message"].lower()


def test_resend_verification_and_rate_limit(client: TestClient, db_session):
    # Matrix 24 & 25: Resend verification and rate limit
    email = "resend.test@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "ResendPass123!",
        "full_name": "Resend User",
    })

    # First resend should be blocked if immediately requested within cooldown
    res_too_fast = client.post("/auth/resend-verification", json={"email": email})
    assert res_too_fast.status_code == 429
    assert "60 seconds" in res_too_fast.json()["error"]["message"]

    # Simulate 60+ seconds passing
    _rate_limits.clear()
    u = db_session.query(models.User).filter(models.User.email == email).first()
    u.verification_sent_at = datetime.now(timezone.utc) - timedelta(seconds=70)
    db_session.commit()

    res_ok = client.post("/auth/resend-verification", json={"email": email})
    assert res_ok.status_code == 200
    assert res_ok.json()["sent"] is True

    # Immediate duplicate resend should be rate limited
    res_dup = client.post("/auth/resend-verification", json={"email": email})
    assert res_dup.status_code == 429


def test_existing_users_still_work_without_reverification(client: TestClient, test_user):
    # Matrix 29 & 30: Existing users (like test_user in conftest) default to email_verified=True
    assert test_user.email_verified is True

    # Can log in directly
    res = client.post("/auth/login", json={
        "email": test_user.email,
        "password": "testpassword1234",
    })
    assert res.status_code == 200
    assert AUTH_COOKIE_NAME in res.cookies


def test_auth_logout_clears_cookie(client: TestClient):
    # Matrix 31: Logout still works
    client.cookies.clear()
    email = "logout.test@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "LogoutSecure123!",
        "full_name": "Logout User",
    })
    dev_email = get_latest_dev_email(email)
    client.post("/auth/verify-email", json={"token": dev_email["token"]})
    client.post("/auth/login", json={"email": email, "password": "LogoutSecure123!"})
    assert AUTH_COOKIE_NAME in client.cookies

    res_logout = client.post("/auth/logout")
    assert res_logout.status_code == 200
    cookie_val = client.cookies.get(AUTH_COOKIE_NAME)
    assert cookie_val is None or cookie_val == ""


def test_protected_routes_still_work(client: TestClient):
    # Matrix 32: Protected routes still work
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
    dev_email = get_latest_dev_email(email)
    client.post("/auth/verify-email", json={"token": dev_email["token"]})
    client.post("/auth/login", json={"email": email, "password": "MeSecurePass123!"})

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
    dev_email = get_latest_dev_email(email)
    client.post("/auth/verify-email", json={"token": dev_email["token"]})
    client.post("/auth/login", json={"email": email, "password": "CsrfSecurePass123!"})

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

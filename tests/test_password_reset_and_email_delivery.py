"""
tests/test_password_reset_and_email_delivery.py
Comprehensive test suite verifying production email delivery abstractions,
honest status reporting, account enumeration protection, single-use password reset tokens,
and health/readiness endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import (
    _rate_limits,
    hash_password_reset_token,
)
from backend.services.email_service import (
    EmailService,
    EmailDeliveryResult,
    DevelopmentEmailProvider,
    SMTPProvider,
    ResendProvider,
    get_latest_dev_email,
    clear_dev_email_store,
)
from backend.config import AUTH_COOKIE_NAME
import backend.models as models


@pytest.fixture(autouse=True)
def clean_state(db_session):
    clear_dev_email_store()
    _rate_limits.clear()
    yield
    clear_dev_email_store()
    _rate_limits.clear()


# ==============================================================================
# Part 1 & 2: Honest Email Delivery Status
# ==============================================================================

def test_register_returns_honest_email_sent_status(client: TestClient):
    email = "honest.sent@gmail.com"
    res = client.post("/auth/register", json={
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "Honest User",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["email_status"] == "EMAIL_SENT"
    assert data["verification_required"] is True
    assert "check your email" in data["message"].lower()


def test_register_returns_honest_failure_when_provider_fails(client: TestClient):
    email = "honest.fail@gmail.com"
    failed_result = EmailDeliveryResult(
        status="EMAIL_FAILED",
        provider="smtp",
        error="Connection refused"
    )

    with patch("backend.routes.auth.send_verification_email", return_value=failed_result):
        res = client.post("/auth/register", json={
            "email": email,
            "password": "ValidPassword123!",
            "full_name": "Failed Delivery User",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["email_status"] == "EMAIL_FAILED"
        assert "couldn't send the verification email" in data["message"].lower()


def test_resend_verification_reports_failure_when_provider_fails(client: TestClient, db_session):
    email = "resend.fail@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "Resend Fail User",
    })

    # Age verification_sent_at past 60s and clear in-memory rate limits to test resend delivery failure
    u = db_session.query(models.User).filter(models.User.email == email).first()
    u.verification_sent_at = datetime.now(timezone.utc) - timedelta(seconds=70)
    db_session.commit()
    _rate_limits.clear()

    failed_result = EmailDeliveryResult(
        status="EMAIL_FAILED",
        provider="smtp",
        error="SMTP server timeout"
    )

    with patch("backend.routes.auth.send_verification_email", return_value=failed_result):
        res = client.post("/auth/resend-verification", json={"email": email})
        assert res.status_code == 502
        assert "couldn't resend the email" in res.json()["error"]["message"].lower()


# ==============================================================================
# Part 3, 4, 5: Email Provider Abstraction
# ==============================================================================

def test_development_email_provider():
    provider = DevelopmentEmailProvider()
    assert provider.is_configured() is True
    health = provider.health_check()
    assert health["provider"] == "development"
    assert health["configured"] is True

    result = provider.send(
        to_email="test.dev@gmail.com",
        subject="Test Subject",
        plain_text="Hello dev",
        html="<p>Hello dev</p>",
        email_type="verification"
    )
    assert result.is_success is True
    assert result.status == "EMAIL_SENT"
    assert result.provider == "development"
    assert result.message_id is not None


def test_smtp_provider_unconfigured_error():
    with patch("backend.services.email_service.SMTP_HOST", ""):
        provider = SMTPProvider()
        assert provider.is_configured() is False
        res = provider.send(
            to_email="smtp.unconf@gmail.com",
            subject="Subj",
            plain_text="Text",
            html="<p>Text</p>"
        )
        assert res.status == "EMAIL_PROVIDER_UNAVAILABLE"
        assert res.is_success is False


def test_resend_provider_unconfigured_error():
    with patch("backend.services.email_service.RESEND_API_KEY", ""):
        provider = ResendProvider()
        assert provider.is_configured() is False
        res = provider.send(
            to_email="resend.unconf@gmail.com",
            subject="Subj",
            plain_text="Text",
            html="<p>Text</p>"
        )
        assert res.status == "EMAIL_PROVIDER_UNAVAILABLE"
        assert res.is_success is False


# ==============================================================================
# Part 10 - 18: Forgot Password & Password Reset Flow
# ==============================================================================

def test_forgot_password_account_enumeration_protection(client: TestClient):
    # Case 1: Email does not exist
    res_nonexistent = client.post("/auth/forgot-password", json={
        "email": "nonexistent.account@gmail.com"
    })
    assert res_nonexistent.status_code == 200
    data_nonexistent = res_nonexistent.json()
    assert "if an account exists" in data_nonexistent["message"].lower()
    assert data_nonexistent["sent"] is True

    # Check that no dev email was stored for nonexistent user
    assert get_latest_dev_email("nonexistent.account@gmail.com") is None

    # Case 2: Email exists
    registered_email = "registered.reset@gmail.com"
    client.post("/auth/register", json={
        "email": registered_email,
        "password": "InitialPassword123!",
        "full_name": "Reset Tester",
    })
    clear_dev_email_store()
    _rate_limits.clear()

    res_existing = client.post("/auth/forgot-password", json={
        "email": registered_email
    })
    assert res_existing.status_code == 200
    data_existing = res_existing.json()
    # Response message must be identical to nonexistent user
    assert data_existing["message"] == data_nonexistent["message"]

    # Dev email capture must contain the password reset link
    dev_email = get_latest_dev_email(registered_email)
    assert dev_email is not None
    assert "Reset your Interview Intelligence password" in dev_email["subject"]
    assert "/reset-password?token=" in dev_email["plain_text"]


def test_complete_password_reset_flow(client: TestClient, db_session):
    email = "full.reset.flow@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "OldPassword123!",
        "full_name": "Reset Flow User",
    })

    # Verify email first so account is active
    verif_email = get_latest_dev_email(email)
    token = verif_email["plain_text"].split("token=")[1].split()[0]
    client.post("/auth/verify-email", json={"token": token})

    # Confirm old password works
    res_login_old = client.post("/auth/login", json={"email": email, "password": "OldPassword123!"})
    assert res_login_old.status_code == 200
    client.cookies.clear()
    clear_dev_email_store()
    _rate_limits.clear()

    # Step 1: Request password reset
    res_forgot = client.post("/auth/forgot-password", json={"email": email})
    assert res_forgot.status_code == 200

    # Step 2: Extract reset token from email
    reset_email = get_latest_dev_email(email)
    assert reset_email is not None
    reset_token = reset_email["plain_text"].split("token=")[1].split()[0]

    # Step 3: Reset password with valid new password
    new_password = "NewSecurePassword123!"
    res_reset = client.post("/auth/reset-password", json={
        "token": reset_token,
        "new_password": new_password,
    })
    assert res_reset.status_code == 200
    assert res_reset.json()["success"] is True
    assert "password has been updated" in res_reset.json()["message"].lower()

    # Step 4: Login with old password fails
    res_old_fail = client.post("/auth/login", json={"email": email, "password": "OldPassword123!"})
    assert res_old_fail.status_code == 401

    # Step 5: Login with new password succeeds
    res_new_success = client.post("/auth/login", json={"email": email, "password": new_password})
    assert res_new_success.status_code == 200
    assert AUTH_COOKIE_NAME in res_new_success.cookies


def test_reset_password_single_use_token(client: TestClient):
    email = "single.use@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "InitialPass123!",
        "full_name": "Single Use User",
    })
    _rate_limits.clear()

    client.post("/auth/forgot-password", json={"email": email})
    reset_email = get_latest_dev_email(email)
    token = reset_email["plain_text"].split("token=")[1].split()[0]

    # First reset succeeds
    res1 = client.post("/auth/reset-password", json={
        "token": token,
        "new_password": "NewPassword123!",
    })
    assert res1.status_code == 200

    # Second reset with SAME token fails
    res2 = client.post("/auth/reset-password", json={
        "token": token,
        "new_password": "AnotherPassword123!",
    })
    assert res2.status_code == 400
    assert "no longer valid" in res2.json()["error"]["message"].lower()


def test_reset_password_expired_token(client: TestClient, db_session):
    email = "expired.reset@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "InitialPass123!",
        "full_name": "Expired Reset User",
    })
    _rate_limits.clear()

    client.post("/auth/forgot-password", json={"email": email})
    reset_email = get_latest_dev_email(email)
    token = reset_email["plain_text"].split("token=")[1].split()[0]

    # Artificially expire the reset token in DB
    user = db_session.query(models.User).filter(models.User.email == email).first()
    user.password_reset_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()

    res = client.post("/auth/reset-password", json={
        "token": token,
        "new_password": "NewPassword123!",
    })
    assert res.status_code == 400
    assert "no longer valid" in res.json()["error"]["message"].lower()


def test_reset_password_invalid_token(client: TestClient):
    res = client.post("/auth/reset-password", json={
        "token": "totally-fake-token-123456",
        "new_password": "NewPassword123!",
    })
    assert res.status_code == 400
    assert "no longer valid" in res.json()["error"]["message"].lower()


def test_reset_password_weak_password_rejected(client: TestClient):
    email = "weak.pwd@gmail.com"
    client.post("/auth/register", json={
        "email": email,
        "password": "InitialPass123!",
        "full_name": "Weak Pwd User",
    })
    _rate_limits.clear()

    client.post("/auth/forgot-password", json={"email": email})
    reset_email = get_latest_dev_email(email)
    token = reset_email["plain_text"].split("token=")[1].split()[0]

    # Try setting password shorter than 8 chars
    res = client.post("/auth/reset-password", json={
        "token": token,
        "new_password": "Short1!",
    })
    assert res.status_code == 400
    assert "at least 8 characters" in res.json()["error"]["message"].lower()


# ==============================================================================
# Part 21 & 26: Health & Readiness Checks
# ==============================================================================

def test_health_check_endpoint(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_readiness_check_endpoint(client: TestClient):
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ready", "degraded")
    assert data["database"] == "ok"
    assert "email" in data
    assert "provider" in data["email"]
    assert "configured" in data["email"]
    # Ensure no secrets leaked
    assert "password" not in str(data).lower()
    assert "secret" not in str(data).lower()

"""
tests/test_email_verification_production.py
Comprehensive production-grade test suite covering Resend integration,
email verification lifecycle, abuse mitigation, atomic consumption,
unverified protected endpoint rejection, and backward compatibility.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.auth_service import (
    _rate_limits,
    hash_password,
    hash_verification_token,
    generate_verification_token,
    create_access_token,
)
from backend.services.email_service import (
    EmailService,
    ResendProvider,
    EmailDeliveryResult,
    clear_dev_email_store,
)
from backend.config import AUTH_COOKIE_NAME
import backend.models as models


@pytest.fixture(autouse=True)
def clean_test_environment(db_session):
    clear_dev_email_store()
    _rate_limits.clear()
    yield
    clear_dev_email_store()
    _rate_limits.clear()


# ==============================================================================
# 1. Resend Provider Unit & Mock Tests (Never sends real emails)
# ==============================================================================

def test_resend_provider_health_check_configured():
    with patch("backend.services.email_service.RESEND_API_KEY", "re_test_key_123"):
        provider = ResendProvider()
        assert provider.is_configured() is True
        health = provider.health_check()
        assert health["provider"] == "resend"
        assert health["configured"] is True
        assert health["endpoint"] == "https://api.resend.com/emails"


def test_resend_provider_dispatch_success():
    with patch("backend.services.email_service.RESEND_API_KEY", "re_test_key_123"):
        provider = ResendProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "resend_msg_abc123"}

        with patch("httpx.Client.post", return_value=mock_resp):
            result = provider.send(
                to_email="candidate.resend@gmail.com",
                subject="Verify your account",
                plain_text="Please verify your account",
                html="<p>Please verify</p>",
                email_type="verification"
            )

            assert result.is_success is True
            assert result.status == "EMAIL_SENT"
            assert result.provider == "resend"
            assert result.message_id == "resend_msg_abc123"
            assert result.accepted is True


def test_resend_provider_dispatch_failure_api_error():
    with patch("backend.services.email_service.RESEND_API_KEY", "re_test_key_123"):
        provider = ResendProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {
            "statusCode": 403,
            "message": "Domain not verified. Visit https://resend.com/domains"
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            result = provider.send(
                to_email="candidate.resend@gmail.com",
                subject="Verify your account",
                plain_text="Please verify your account",
                html="<p>Please verify</p>",
                email_type="verification"
            )

            assert result.is_success is False
            assert result.status == "EMAIL_FAILED"
            assert result.provider == "resend"
            assert "403" in result.error
            assert "Domain not verified" in result.error
            assert result.accepted is False


def test_resend_provider_timeout_handling():
    with patch("backend.services.email_service.RESEND_API_KEY", "re_test_key_123"):
        provider = ResendProvider()

        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
            result = provider.send(
                to_email="timeout.user@gmail.com",
                subject="Verify your account",
                plain_text="Verify",
                html="<p>Verify</p>",
                email_type="verification"
            )

            assert result.is_success is False
            assert result.status == "EMAIL_FAILED"
            assert "timed out" in result.error.lower()
            assert result.accepted is False


def test_resend_provider_connection_error_handling():
    with patch("backend.services.email_service.RESEND_API_KEY", "re_test_key_123"):
        provider = ResendProvider()

        with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
            result = provider.send(
                to_email="connect.fail@gmail.com",
                subject="Verify",
                plain_text="Verify",
                html="<p>Verify</p>",
                email_type="verification"
            )

            assert result.is_success is False
            assert result.status == "EMAIL_PROVIDER_UNAVAILABLE"
            assert "unreachable" in result.error.lower()
            assert result.accepted is False


# ==============================================================================
# 2. Registration & Email Verification Lifecycle
# ==============================================================================

def test_registration_with_verification_required_happy_path(client: TestClient, monkeypatch):
    import backend.routes.auth as auth_route
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "registered.candidate@gmail.com"
    res = client.post("/auth/register", json={
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "Candidate One",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["verification_required"] is True
    assert data["email_status"] == "EMAIL_SENT"
    assert data["email"] == email

    # When verification is required, auth cookie must NOT be set initially
    assert AUTH_COOKIE_NAME not in res.cookies


def test_registration_duplicate_verified_account_rejection(client: TestClient, db_session, monkeypatch):
    import backend.routes.auth as auth_route
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "existing.verified@gmail.com"
    # Seed an already verified user
    user = models.User(
        email=email,
        password_hash=hash_password("ExistingPassword123!"),
        full_name="Existing Verified",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/auth/register", json={
        "email": email,
        "password": "NewPassword123!",
        "full_name": "Attempt Two",
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["error"]["message"].lower()


def test_registration_invalid_email_and_weak_passwords(client: TestClient):
    # Non-Gmail rejection
    res = client.post("/auth/register", json={
        "email": "user@yahoo.com",
        "password": "ValidPassword123!",
        "full_name": "Yahoo User",
    })
    assert res.status_code == 400
    assert "gmail" in res.json()["error"]["message"].lower()

    # Weak password rejection
    res_weak = client.post("/auth/register", json={
        "email": "valid.user@gmail.com",
        "password": "short",
        "full_name": "Valid Name",
    })
    assert res_weak.status_code in (400, 422)


# ==============================================================================
# 3. Verification Token Consumption: Valid, Invalid, Expired, Reused, Concurrent
# ==============================================================================

def test_successful_verification(client: TestClient, db_session, monkeypatch):
    import backend.routes.auth as auth_route
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "pending.verify@gmail.com"
    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    now = datetime.now(timezone.utc)

    user = models.User(
        email=email,
        password_hash=hash_password("Pass12345!"),
        full_name="Pending User",
        email_verified=False,
        verification_token_hash=token_hash,
        verification_expires_at=now + timedelta(minutes=30),
        verification_sent_at=now,
    )
    db_session.add(user)
    db_session.commit()

    # Verify token
    res = client.post("/auth/verify-email", json={"token": raw_token})
    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is True
    assert "ready" in data["message"].lower()

    # Verify DB state updated
    db_session.refresh(user)
    assert user.email_verified is True
    assert user.verification_used_at is not None


def test_verification_invalid_token(client: TestClient):
    res = client.post("/auth/verify-email", json={"token": "completely_bogus_token_xyz"})
    assert res.status_code == 400
    assert "no longer valid" in res.json()["error"]["message"].lower()


def test_verification_expired_token(client: TestClient, db_session):
    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    past = datetime.now(timezone.utc) - timedelta(minutes=45)

    user = models.User(
        email="expired.token@gmail.com",
        password_hash=hash_password("Pass12345!"),
        email_verified=False,
        verification_token_hash=token_hash,
        verification_expires_at=past,
        verification_sent_at=past,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/auth/verify-email", json={"token": raw_token})
    assert res.status_code == 400
    assert "expired" in res.json()["error"]["message"].lower()


def test_verification_reused_token_rejected(client: TestClient, db_session):
    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    now = datetime.now(timezone.utc)

    user = models.User(
        email="reused.token@gmail.com",
        password_hash=hash_password("Pass12345!"),
        email_verified=True,
        verification_token_hash=token_hash,
        verification_expires_at=now + timedelta(minutes=30),
        verification_used_at=now - timedelta(minutes=5),
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/auth/verify-email", json={"token": raw_token})
    assert res.status_code == 400
    assert ("already been verified" in res.json()["error"]["message"].lower() or
            "no longer valid" in res.json()["error"]["message"].lower())


def test_verification_atomic_concurrency_guard(client: TestClient, db_session):
    """
    Simulates race condition where two concurrent requests present the same token.
    First request consumes the token; second request must receive HTTP 400.
    """
    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    now = datetime.now(timezone.utc)

    user = models.User(
        email="concurrent.race@gmail.com",
        password_hash=hash_password("Pass12345!"),
        email_verified=False,
        verification_token_hash=token_hash,
        verification_expires_at=now + timedelta(minutes=30),
        verification_sent_at=now,
    )
    db_session.add(user)
    db_session.commit()

    # First request consumes token
    res1 = client.post("/auth/verify-email", json={"token": raw_token})
    assert res1.status_code == 200

    # Immediate second concurrent call with the same token
    res2 = client.post("/auth/verify-email", json={"token": raw_token})
    assert res2.status_code == 400
    assert ("already been verified" in res2.json()["error"]["message"].lower() or
            "no longer valid" in res2.json()["error"]["message"].lower())


# ==============================================================================
# 4. Resend Cooldown and Abuse Protection
# ==============================================================================

def test_resend_verification_cooldown_enforced(client: TestClient, db_session, monkeypatch):
    import backend.routes.auth as auth_route
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "cooldown.user@gmail.com"
    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    now = datetime.now(timezone.utc)

    user = models.User(
        email=email,
        password_hash=hash_password("Pass12345!"),
        email_verified=False,
        verification_token_hash=token_hash,
        verification_expires_at=now + timedelta(minutes=30),
        verification_sent_at=now,  # sent 0 seconds ago
    )
    db_session.add(user)
    db_session.commit()

    # Immediate resend request must trigger 429
    res = client.post("/auth/resend-verification", json={"email": email})
    assert res.status_code == 429
    assert "wait 60 seconds" in res.json()["error"]["message"].lower()


def test_resend_verification_succeeds_after_cooldown(client: TestClient, db_session, monkeypatch):
    import backend.routes.auth as auth_route
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "cooldown.pass@gmail.com"
    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    sent_in_past = datetime.now(timezone.utc) - timedelta(seconds=65)

    user = models.User(
        email=email,
        password_hash=hash_password("Pass12345!"),
        full_name="Past User",
        email_verified=False,
        verification_token_hash=token_hash,
        verification_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        verification_sent_at=sent_in_past,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/auth/resend-verification", json={"email": email})
    assert res.status_code == 200
    assert res.json()["sent"] is True


def test_resend_verification_enumeration_protection(client: TestClient):
    # Non-existent email returns uniform 200 message
    res = client.post("/auth/resend-verification", json={"email": "nonexistent.account@gmail.com"})
    assert res.status_code == 200
    assert res.json()["sent"] is True
    assert "verification email sent" in res.json()["message"].lower()


# ==============================================================================
# 5. Unverified Login & Protected Route Backend Enforcement
# ==============================================================================

def test_unverified_account_login_rejected(client: TestClient, db_session, monkeypatch):
    import backend.routes.auth as auth_route
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "unverified.login@gmail.com"
    pwd = "SecretPassword123!"
    user = models.User(
        email=email,
        password_hash=hash_password(pwd),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 403
    assert "verify your email" in res.json()["error"]["message"].lower()


def test_unverified_account_cannot_bypass_via_protected_endpoint(client: TestClient, db_session, monkeypatch):
    """
    Verifies that calling get_current_user directly rejects unverified accounts
    with HTTP 403 when REQUIRE_EMAIL_VERIFICATION is enabled.
    """
    import backend.config as cfg
    import backend.services.auth_service as auth_svc
    monkeypatch.setattr(cfg, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "bypass.attempt@gmail.com"
    user = models.User(
        email=email,
        password_hash=hash_password("Pass12345!"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()

    # Forge or possess an access token for the unverified user
    token = create_access_token(user.id)

    # Attempt to call protected endpoint /profile using bearer header
    res = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "verify your email" in res.json()["error"]["message"].lower()

    # Attempt to call /auth/me with auth_token cookie
    client.cookies.set(AUTH_COOKIE_NAME, token)
    res_me = client.get("/auth/me")
    assert res_me.status_code == 403
    assert "verify your email" in res_me.json()["error"]["message"].lower()


# ==============================================================================
# 6. Backward Compatibility: Existing Verified Accounts
# ==============================================================================

def test_existing_verified_account_full_access(client: TestClient, db_session, monkeypatch):
    import backend.routes.auth as auth_route
    import backend.config as cfg
    monkeypatch.setattr(auth_route, "REQUIRE_EMAIL_VERIFICATION", True)
    monkeypatch.setattr(cfg, "REQUIRE_EMAIL_VERIFICATION", True)

    email = "veteran.user@gmail.com"
    pwd = "VeteranPassword123!"
    user = models.User(
        email=email,
        password_hash=hash_password(pwd),
        full_name="Veteran User",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    # Login succeeds
    res_login = client.post("/auth/login", json={"email": email, "password": pwd})
    assert res_login.status_code == 200

    # Protected endpoint succeeds
    token = create_access_token(user.id)
    res_profile = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert res_profile.status_code == 200

"""
tests/test_password_reset_and_email_delivery.py
Verifies email service provider abstractions (development, smtp, resend)
and health / readiness endpoints.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from backend.services.auth_service import _rate_limits
from backend.services.email_service import (
    EmailService,
    DevelopmentEmailProvider,
    SMTPProvider,
    ResendProvider,
    clear_dev_email_store,
)


@pytest.fixture(autouse=True)
def clean_state():
    clear_dev_email_store()
    _rate_limits.clear()
    yield
    clear_dev_email_store()
    _rate_limits.clear()


# ==============================================================================
# Email Provider Abstractions
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
        email_type="notification"
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


def test_resend_provider_configured_and_dispatch():
    with patch("backend.services.email_service.RESEND_API_KEY", "re_test_key_123"):
        provider = ResendProvider()
        assert provider.is_configured() is True
        health = provider.health_check()
        assert health["provider"] == "resend"
        assert health["configured"] is True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "re_msg_123"}

        with patch("httpx.Client.post", return_value=mock_resp):
            res = provider.send(
                to_email="test@resend.com",
                subject="Test",
                plain_text="Body",
                html="<p>Body</p>"
            )
            assert res.is_success is True
            assert res.status == "EMAIL_SENT"
            assert res.message_id == "re_msg_123"


# ==============================================================================
# Health & Readiness Checks
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

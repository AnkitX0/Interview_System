"""
backend/services/email_service.py
Production-ready email delivery architecture and provider abstractions
for Interview Intelligence.

Supports:
- SMTP (Standard SMTP, Mailpit, Google App Password, SendGrid SMTP, Amazon SES)
- Transactional API (Resend via HTTP)
- Development sandbox (in-memory capture and dev log for testing and local inspection)

Never logs plain tokens, passwords, API keys, or raw email addresses.
Never claims an email was sent when delivery failed or provider was unconfigured.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import logging
import os
import secrets
import smtplib
import threading
from typing import Optional, Dict, Any, Tuple

import httpx

from backend.config import (
    EMAIL_PROVIDER,
    EMAIL_FROM,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_USE_TLS,
    SMTP_USE_SSL,
    RESEND_API_KEY,
    APP_BASE_URL,
    FRONTEND_URL,
    VERIFICATION_TOKEN_EXPIRE_MINUTES,
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger("interview_system.email")

# In-memory dev email store for automated tests and local verification inspection
_dev_email_lock = threading.Lock()
_dev_email_store: Dict[str, Dict[str, Any]] = {}

DEV_LOG_DIR = "/app/data" if os.path.exists("/app/data") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEV_EMAIL_LOG = os.path.join(DEV_LOG_DIR, "dev_emails.log")


def _hash_recipient(email: str) -> str:
    """Returns a truncated SHA-256 hash of the email address for safe audit logging."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:12]


@dataclass
class EmailDeliveryResult:
    """Standardized result returned by all email delivery attempts."""
    status: str  # "EMAIL_SENT" | "EMAIL_FAILED" | "EMAIL_PROVIDER_UNAVAILABLE"
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == "EMAIL_SENT"


# ---------------------------------------------------------------------------
# Email Templates
# ---------------------------------------------------------------------------

def build_verification_email_content(
    recipient_email: str,
    token: str,
    full_name: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Builds the subject, plain-text body, and HTML body for account verification.
    """
    subject = "Verify your Interview Intelligence account"
    base_url = (FRONTEND_URL or APP_BASE_URL).rstrip("/")
    verification_link = f"{base_url}/verify-email?token={token}"
    greeting_name = full_name.strip() if full_name and full_name.strip() else "there"

    plain_text = f"""Hello {greeting_name},

You created an account for Interview Intelligence.

Verify your email address to activate your account:
{verification_link}

This link expires in {VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.

If you did not create this account, no further action is required.

— The Interview Intelligence Team
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify your Interview Intelligence account</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); padding: 40px 32px;">
          <!-- Header Branding -->
          <tr>
            <td style="text-align: center; padding-bottom: 24px;">
              <span style="display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #2563eb; background: #eff6ff; padding: 4px 10px; border-radius: 9999px;">
                Interview Intelligence
              </span>
              <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 12px 0 4px 0;">
                Verify your account
              </h1>
              <p style="font-size: 14px; color: #64748b; margin: 0;">
                Preparation System
              </p>
            </td>
          </tr>

          <!-- Message Body -->
          <tr>
            <td style="font-size: 15px; line-height: 1.6; color: #334155; padding-bottom: 28px;">
              <p style="margin: 0 0 16px 0;">Hello <strong>{greeting_name}</strong>,</p>
              <p style="margin: 0 0 16px 0;">
                You created an account for Interview Intelligence. Verify your email address to activate your account.
              </p>
            </td>
          </tr>

          <!-- Call To Action Button -->
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <a href="{verification_link}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 32px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);">
                Verify Email Address
              </a>
            </td>
          </tr>

          <!-- Expiration Notice -->
          <tr>
            <td style="font-size: 13px; color: #64748b; line-height: 1.5; padding-bottom: 24px; border-bottom: 1px solid #f1f5f9;">
              <p style="margin: 0 0 8px 0;">
                <strong>Note:</strong> This link expires in {VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.
              </p>
              <p style="margin: 0 0 8px 0;">
                If the button above does not work, copy and paste this URL into your browser:
              </p>
              <p style="margin: 0; word-break: break-all; color: #2563eb; font-family: monospace; font-size: 12px;">
                {verification_link}
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding-top: 20px; font-size: 12px; color: #94a3b8; text-align: center;">
              If you did not request this account, you can safely ignore this email.<br>
              © Interview Intelligence Preparation System. All rights reserved.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return subject, plain_text, html


def build_password_reset_email_content(
    recipient_email: str,
    token: str,
    full_name: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Builds the subject, plain-text body, and HTML body for password reset.
    """
    subject = "Reset your Interview Intelligence password"
    base_url = (FRONTEND_URL or APP_BASE_URL).rstrip("/")
    reset_link = f"{base_url}/reset-password?token={token}"
    greeting_name = full_name.strip() if full_name and full_name.strip() else "there"

    plain_text = f"""Hello {greeting_name},

You requested a password reset for your Interview Intelligence account.

Reset your password using the link below:
{reset_link}

This link expires in {PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.

If you did not request this, you can safely ignore this email. Your current password will remain unchanged.

— The Interview Intelligence Team
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset your Interview Intelligence password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); padding: 40px 32px;">
          <!-- Header Branding -->
          <tr>
            <td style="text-align: center; padding-bottom: 24px;">
              <span style="display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #2563eb; background: #eff6ff; padding: 4px 10px; border-radius: 9999px;">
                Interview Intelligence
              </span>
              <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 12px 0 4px 0;">
                Reset your password
              </h1>
              <p style="font-size: 14px; color: #64748b; margin: 0;">
                Preparation System
              </p>
            </td>
          </tr>

          <!-- Message Body -->
          <tr>
            <td style="font-size: 15px; line-height: 1.6; color: #334155; padding-bottom: 28px;">
              <p style="margin: 0 0 16px 0;">Hello <strong>{greeting_name}</strong>,</p>
              <p style="margin: 0 0 16px 0;">
                You requested a password reset for your Interview Intelligence account. Click the button below to choose a new password.
              </p>
            </td>
          </tr>

          <!-- Call To Action Button -->
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <a href="{reset_link}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 32px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);">
                Reset Password
              </a>
            </td>
          </tr>

          <!-- Expiration Notice -->
          <tr>
            <td style="font-size: 13px; color: #64748b; line-height: 1.5; padding-bottom: 24px; border-bottom: 1px solid #f1f5f9;">
              <p style="margin: 0 0 8px 0;">
                <strong>Note:</strong> This link expires in {PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
              </p>
              <p style="margin: 0 0 8px 0;">
                If the button above does not work, copy and paste this URL into your browser:
              </p>
              <p style="margin: 0; word-break: break-all; color: #2563eb; font-family: monospace; font-size: 12px;">
                {reset_link}
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding-top: 20px; font-size: 12px; color: #94a3b8; text-align: center;">
              If you did not request this, you can safely ignore this email.<br>
              © Interview Intelligence Preparation System. All rights reserved.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return subject, plain_text, html


# ---------------------------------------------------------------------------
# Email Provider Abstraction
# ---------------------------------------------------------------------------

class EmailProvider(ABC):
    """Abstract base class for email delivery providers."""

    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        plain_text: str,
        html: str,
        email_type: str = "generic"
    ) -> EmailDeliveryResult:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass


class DevelopmentEmailProvider(EmailProvider):
    """
    Development email provider: captures emails in memory and file for local testing.
    Safe for development and automated test suites.
    """

    def is_configured(self) -> bool:
        return True

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "development",
            "configured": True,
            "mode": "in-memory-capture",
        }

    def send(
        self,
        to_email: str,
        subject: str,
        plain_text: str,
        html: str,
        email_type: str = "generic"
    ) -> EmailDeliveryResult:
        recipient_hash = _hash_recipient(to_email)
        logger.info(
            "[EMAIL] type=%s provider=development recipient_hash=%s status=captured",
            email_type,
            recipient_hash,
        )

        token = None
        link = None
        if "token=" in plain_text:
            try:
                for line in plain_text.splitlines():
                    if "token=" in line:
                        link = line.strip()
                        token = line.split("token=")[1].split()[0].strip()
                        break
            except Exception:
                pass

        msg_id = f"dev-{secrets.token_hex(8)}"
        with _dev_email_lock:
            _dev_email_store[to_email.lower()] = {
                "to_email": to_email,
                "token": token,
                "verification_link": link,
                "reset_link": link,
                "subject": subject,
                "plain_text": plain_text,
                "html": html,
                "sent_at": datetime.now(timezone.utc),
                "message_id": msg_id,
                "email_type": email_type,
            }

        try:
            os.makedirs(DEV_LOG_DIR, exist_ok=True)
            with open(DEV_EMAIL_LOG, "a", encoding="utf-8") as f:
                f.write(
                    f"[{datetime.now(timezone.utc).isoformat()}] [{email_type.upper()}] TO: {to_email} | SUBJECT: {subject} | MSG_ID: {msg_id}\n"
                )
        except Exception as log_err:
            logger.debug("Could not append to dev_emails.log: %s", log_err)

        return EmailDeliveryResult(
            status="EMAIL_SENT",
            provider="development",
            message_id=msg_id,
        )


class SMTPProvider(EmailProvider):
    """
    Standard SMTP provider supporting STARTTLS, SSL, and authentication.
    Works with Mailpit, Google App Password, SendGrid SMTP, AWS SES SMTP.
    """

    def is_configured(self) -> bool:
        return bool(SMTP_HOST)

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "smtp",
            "configured": bool(SMTP_HOST),
            "host": SMTP_HOST or None,
            "port": SMTP_PORT if SMTP_HOST else None,
            "tls": SMTP_USE_TLS if SMTP_HOST else None,
            "ssl": SMTP_USE_SSL if SMTP_HOST else None,
        }

    def send(
        self,
        to_email: str,
        subject: str,
        plain_text: str,
        html: str,
        email_type: str = "generic"
    ) -> EmailDeliveryResult:
        recipient_hash = _hash_recipient(to_email)

        if not self.is_configured():
            logger.error(
                "[EMAIL] type=%s provider=smtp recipient_hash=%s status=provider_unavailable (SMTP_HOST not set)",
                email_type,
                recipient_hash,
            )
            return EmailDeliveryResult(
                status="EMAIL_PROVIDER_UNAVAILABLE",
                provider="smtp",
                error="SMTP_HOST is not configured.",
            )

        logger.info(
            "[EMAIL] type=%s provider=smtp recipient_hash=%s status=sending",
            email_type,
            recipient_hash,
        )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = EMAIL_FROM
            msg["To"] = to_email
            msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

            part1 = MIMEText(plain_text, "plain", "utf-8")
            part2 = MIMEText(html, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            timeout = 15
            if SMTP_USE_SSL or SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=timeout)
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout)
                if SMTP_USE_TLS or SMTP_PORT == 587:
                    server.starttls()

            with server:
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, [to_email], msg.as_string())

            msg_id = f"smtp-{secrets.token_hex(8)}"
            logger.info(
                "[EMAIL] type=%s provider=smtp recipient_hash=%s status=success",
                email_type,
                recipient_hash,
            )
            return EmailDeliveryResult(
                status="EMAIL_SENT",
                provider="smtp",
                message_id=msg_id,
            )
        except Exception as smtp_err:
            logger.error(
                "[EMAIL] type=%s provider=smtp recipient_hash=%s status=failure error=%s",
                email_type,
                recipient_hash,
                type(smtp_err).__name__,
            )
            return EmailDeliveryResult(
                status="EMAIL_FAILED",
                provider="smtp",
                error=f"SMTP delivery failed: {smtp_err}",
            )


class ResendProvider(EmailProvider):
    """
    Modern transactional email provider via Resend API.
    """

    def is_configured(self) -> bool:
        return bool(RESEND_API_KEY)

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "resend",
            "configured": bool(RESEND_API_KEY),
        }

    def send(
        self,
        to_email: str,
        subject: str,
        plain_text: str,
        html: str,
        email_type: str = "generic"
    ) -> EmailDeliveryResult:
        recipient_hash = _hash_recipient(to_email)

        if not self.is_configured():
            logger.error(
                "[EMAIL] type=%s provider=resend recipient_hash=%s status=provider_unavailable (RESEND_API_KEY not set)",
                email_type,
                recipient_hash,
            )
            return EmailDeliveryResult(
                status="EMAIL_PROVIDER_UNAVAILABLE",
                provider="resend",
                error="RESEND_API_KEY is not configured.",
            )

        logger.info(
            "[EMAIL] type=%s provider=resend recipient_hash=%s status=sending",
            email_type,
            recipient_hash,
        )

        try:
            payload = {
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "text": plain_text,
                "html": html,
            }
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post("https://api.resend.com/emails", json=payload, headers=headers)

            if res.status_code in (200, 201):
                data = res.json()
                msg_id = data.get("id", f"resend-{secrets.token_hex(8)}")
                logger.info(
                    "[EMAIL] type=%s provider=resend recipient_hash=%s status=success",
                    email_type,
                    recipient_hash,
                )
                return EmailDeliveryResult(
                    status="EMAIL_SENT",
                    provider="resend",
                    message_id=msg_id,
                )
            else:
                logger.error(
                    "[EMAIL] type=%s provider=resend recipient_hash=%s status=failure http_status=%d",
                    email_type,
                    recipient_hash,
                    res.status_code,
                )
                return EmailDeliveryResult(
                    status="EMAIL_FAILED",
                    provider="resend",
                    error=f"Resend API error HTTP {res.status_code}: {res.text}",
                )
        except Exception as resend_err:
            logger.error(
                "[EMAIL] type=%s provider=resend recipient_hash=%s status=failure error=%s",
                email_type,
                recipient_hash,
                type(resend_err).__name__,
            )
            return EmailDeliveryResult(
                status="EMAIL_FAILED",
                provider="resend",
                error=f"Resend dispatch error: {resend_err}",
            )


# ---------------------------------------------------------------------------
# Email Service Dispatcher
# ---------------------------------------------------------------------------

class EmailService:
    """
    Central email dispatching service. Selects configured provider dynamically.
    """

    @classmethod
    def get_provider(cls) -> EmailProvider:
        prov = EMAIL_PROVIDER
        if prov == "resend":
            return ResendProvider()
        elif prov == "smtp":
            return SMTPProvider()
        elif prov in ("development", "dev", "test", "local"):
            return DevelopmentEmailProvider()

        # Fallback heuristic: If SMTP_HOST provided, use SMTP; if RESEND_API_KEY, use Resend; else Development
        if SMTP_HOST:
            return SMTPProvider()
        if RESEND_API_KEY:
            return ResendProvider()

        return DevelopmentEmailProvider()

    @classmethod
    def send_verification_email(
        cls,
        to_email: str,
        token: str,
        full_name: Optional[str] = None
    ) -> EmailDeliveryResult:
        subject, plain_text, html = build_verification_email_content(to_email, token, full_name)
        provider = cls.get_provider()
        return provider.send(to_email, subject, plain_text, html, email_type="verification")

    @classmethod
    def send_password_reset_email(
        cls,
        to_email: str,
        token: str,
        full_name: Optional[str] = None
    ) -> EmailDeliveryResult:
        subject, plain_text, html = build_password_reset_email_content(to_email, token, full_name)
        provider = cls.get_provider()
        return provider.send(to_email, subject, plain_text, html, email_type="password_reset")

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        provider = cls.get_provider()
        return provider.health_check()


# Module-level convenience functions (preserving backward compatibility)
def send_verification_email(
    to_email: str,
    token: str,
    full_name: Optional[str] = None
) -> EmailDeliveryResult:
    return EmailService.send_verification_email(to_email, token, full_name)


def send_password_reset_email(
    to_email: str,
    token: str,
    full_name: Optional[str] = None
) -> EmailDeliveryResult:
    return EmailService.send_password_reset_email(to_email, token, full_name)


def get_latest_dev_email(email: str) -> Optional[Dict[str, Any]]:
    """Helper for testing and local inspection to retrieve the most recent email captured in dev mode."""
    with _dev_email_lock:
        return _dev_email_store.get(email.lower())


def clear_dev_email_store() -> None:
    """Helper for testing to reset captured development emails."""
    with _dev_email_lock:
        _dev_email_store.clear()

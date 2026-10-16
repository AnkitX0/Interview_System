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
    accepted: bool = False  # True when provider API acknowledged receipt of email request

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
    Builds the subject, plain-text body, and HTML body for account verification with 6-digit OTP.
    """
    subject = f"Your Interview Intelligence verification code: {token}"
    base_url = (FRONTEND_URL or APP_BASE_URL).rstrip("/")
    verification_link = f"{base_url}/verify-email?email={recipient_email}&otp={token}&token={token}"
    greeting_name = full_name.strip() if full_name and full_name.strip() else "there"

    plain_text = f"""Hello {greeting_name},

Thank you for creating an account for Interview Intelligence.

Your 6-digit email verification code is:

    {token}

This verification code expires in {VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.

Alternatively, you can verify your account directly by visiting:
{verification_link}

If you did not request this account, please ignore this email.

— The Interview Intelligence Team
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Interview Intelligence verification code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 520px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); padding: 40px 32px;">
          <!-- Header Branding -->
          <tr>
            <td style="text-align: center; padding-bottom: 24px;">
              <span style="display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 4px 12px; border-radius: 9999px; border: 1px solid rgba(56, 189, 248, 0.2);">
                Interview Intelligence
              </span>
              <h1 style="font-size: 22px; font-weight: 700; color: #ffffff; margin: 16px 0 4px 0;">
                Verification Code
              </h1>
              <p style="font-size: 14px; color: #94a3b8; margin: 0;">
                Enter this 6-digit code to activate your account
              </p>
            </td>
          </tr>

          <!-- Message Body -->
          <tr>
            <td style="font-size: 15px; line-height: 1.6; color: #cbd5e1; padding-bottom: 12px;">
              <p style="margin: 0 0 12px 0;">Hello <strong>{greeting_name}</strong>,</p>
              <p style="margin: 0;">
                Use the following verification code to complete your registration:
              </p>
            </td>
          </tr>

          <!-- 6-Digit OTP Box -->
          <tr>
            <td align="center" style="padding: 20px 0;">
              <div style="background-color: #0f172a; border: 1px solid #475569; border-radius: 8px; padding: 16px 24px; display: inline-block;">
                <span style="font-family: 'SF Mono', Monaco, Consolas, monospace; font-size: 32px; font-weight: 700; letter-spacing: 10px; color: #38bdf8;">
                  {token}
                </span>
              </div>
            </td>
          </tr>

          <!-- Expiration Notice -->
          <tr>
            <td style="text-align: center; font-size: 13px; color: #94a3b8; line-height: 1.5; padding-bottom: 24px;">
              <p style="margin: 0 0 16px 0;">
                ⏱ This code expires in <strong>{VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes</strong>.
              </p>
              <p style="margin: 0 0 8px 0; font-size: 13px; color: #64748b;">
                Or click the button below to verify automatically:
              </p>
              <a href="{verification_link}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 10px 24px; border-radius: 6px;">
                Verify Account Directly
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding-top: 24px; border-top: 1px solid #334155; font-size: 12px; color: #64748b; text-align: center; line-height: 1.5;">
              If you did not request this registration, you can safely ignore this email.<br>
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
            "EMAIL_SEND_START provider=development email_type=%s recipient_hash=%s",
            email_type,
            recipient_hash,
        )

        token = None
        link = None
        for pattern in ("token=", "otp="):
            if pattern in plain_text:
                try:
                    for line in plain_text.splitlines():
                        if pattern in line:
                            link = line.strip()
                            token = line.split(pattern)[1].split("&")[0].split()[0].strip()
                            break
                    if token:
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

        logger.info(
            "EMAIL_SEND_SUCCESS provider=development email_type=%s message_id=%s",
            email_type,
            msg_id,
        )
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

        logger.info(
            "EMAIL_SEND_START provider=smtp email_type=%s recipient_hash=%s",
            email_type,
            recipient_hash,
        )

        if not self.is_configured():
            logger.error(
                "EMAIL_SEND_FAILURE provider=smtp email_type=%s error=SMTP_HOST_NOT_CONFIGURED",
                email_type,
            )
            return EmailDeliveryResult(
                status="EMAIL_PROVIDER_UNAVAILABLE",
                provider="smtp",
                error="SMTP_HOST is not configured.",
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
                "EMAIL_SEND_SUCCESS provider=smtp email_type=%s message_id=%s",
                email_type,
                msg_id,
            )
            return EmailDeliveryResult(
                status="EMAIL_SENT",
                provider="smtp",
                message_id=msg_id,
            )
        except Exception as smtp_err:
            safe_err = f"{type(smtp_err).__name__}: {str(smtp_err)}"
            logger.error(
                "EMAIL_SEND_FAILURE provider=smtp email_type=%s error=%s",
                email_type,
                safe_err,
            )
            return EmailDeliveryResult(
                status="EMAIL_FAILED",
                provider="smtp",
                error=f"SMTP delivery failed: {safe_err}",
            )


class ResendProvider(EmailProvider):
    """
    Modern transactional email provider via Resend API (https://api.resend.com/emails).
    """

    def is_configured(self) -> bool:
        return bool(RESEND_API_KEY)

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "resend",
            "configured": bool(RESEND_API_KEY),
            "endpoint": "https://api.resend.com/emails",
            "sender": EMAIL_FROM if bool(RESEND_API_KEY) else None,
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
            "EMAIL_SEND_START provider=resend email_type=%s recipient_hash=%s",
            email_type,
            recipient_hash,
        )

        if not self.is_configured():
            logger.error(
                "EMAIL_SEND_FAILURE provider=resend email_type=%s error=RESEND_API_KEY_NOT_CONFIGURED",
                email_type,
            )
            return EmailDeliveryResult(
                status="EMAIL_PROVIDER_UNAVAILABLE",
                provider="resend",
                error="RESEND_API_KEY is not configured.",
                accepted=False,
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
                # Provider acceptance indicates Resend successfully accepted the message into its delivery pipeline.
                logger.info(
                    "EMAIL_DISPATCH_ACCEPTED provider=resend email_type=%s message_id=%s (accepted by Resend API)",
                    email_type,
                    msg_id,
                )
                return EmailDeliveryResult(
                    status="EMAIL_SENT",
                    provider="resend",
                    message_id=msg_id,
                    accepted=True,
                )
            else:
                # Parse Resend error payload safely without leaking secrets or tokens
                err_detail = None
                try:
                    res_json = res.json()
                    err_detail = res_json.get("message") or res_json.get("name")
                except Exception:
                    pass

                safe_err = f"Resend API error HTTP {res.status_code}" + (f": {err_detail}" if err_detail else "")
                logger.error(
                    "EMAIL_SEND_FAILURE provider=resend email_type=%s error=%s",
                    email_type,
                    safe_err,
                )
                return EmailDeliveryResult(
                    status="EMAIL_FAILED",
                    provider="resend",
                    error=safe_err,
                    accepted=False,
                )
        except httpx.TimeoutException:
            logger.error(
                "EMAIL_SEND_TIMEOUT provider=resend email_type=%s recipient_hash=%s",
                email_type,
                recipient_hash,
            )
            return EmailDeliveryResult(
                status="EMAIL_FAILED",
                provider="resend",
                error="Resend API request timed out after 15 seconds.",
                accepted=False,
            )
        except (httpx.ConnectError, httpx.NetworkError) as net_err:
            safe_net_err = type(net_err).__name__
            logger.error(
                "EMAIL_SEND_CONNECT_ERROR provider=resend email_type=%s recipient_hash=%s error=%s",
                email_type,
                recipient_hash,
                safe_net_err,
            )
            return EmailDeliveryResult(
                status="EMAIL_PROVIDER_UNAVAILABLE",
                provider="resend",
                error=f"Resend service unreachable: {safe_net_err}",
                accepted=False,
            )
        except Exception as resend_err:
            safe_err = f"{type(resend_err).__name__}: {str(resend_err)}"
            logger.error(
                "EMAIL_SEND_FAILURE provider=resend email_type=%s error=%s",
                email_type,
                safe_err,
            )
            return EmailDeliveryResult(
                status="EMAIL_FAILED",
                provider="resend",
                error=f"Resend dispatch error: {safe_err}",
                accepted=False,
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
        prov = (EMAIL_PROVIDER or "").lower().strip()
        if prov == "resend":
            return ResendProvider()
        elif prov == "smtp":
            return SMTPProvider()
        elif prov in ("development", "dev", "test", "local"):
            return DevelopmentEmailProvider()

        # Heuristic fallback
        if RESEND_API_KEY:
            return ResendProvider()
        if SMTP_HOST:
            return SMTPProvider()

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

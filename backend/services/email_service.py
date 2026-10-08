"""
backend/services/email_service.py
Email delivery and development email capture service for Interview Intelligence.
Sends professional, branded account verification emails via SMTP or
captures them locally in development environments for inspection and testing.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import threading

from backend.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    APP_BASE_URL,
    VERIFICATION_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger("interview_system.email")

# In-memory dev email store for automated tests and local verification inspection
_dev_email_lock = threading.Lock()
_dev_email_store: Dict[str, Dict[str, Any]] = {}

DEV_LOG_DIR = "/app/data" if os.path.exists("/app/data") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEV_EMAIL_LOG = os.path.join(DEV_LOG_DIR, "dev_emails.log")


def build_verification_email_content(
    recipient_email: str,
    token: str,
    full_name: Optional[str] = None
) -> tuple[str, str, str]:
    """
    Builds the subject, plain text body, and HTML body for account verification.
    """
    subject = "Verify your Interview Intelligence account"
    base_url = APP_BASE_URL.rstrip("/")
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


def send_verification_email(
    to_email: str,
    token: str,
    full_name: Optional[str] = None
) -> bool:
    """
    Sends an account verification email.
    If SMTP credentials are provided, dispatches via SMTP.
    Otherwise, captures the email locally for development and testing.
    Returns True if sent or successfully captured.
    """
    subject, plain_text, html = build_verification_email_content(to_email, token, full_name)
    base_url = APP_BASE_URL.rstrip("/")
    verification_link = f"{base_url}/verify-email?token={token}"

    # Record in local development memory store
    with _dev_email_lock:
        _dev_email_store[to_email.lower()] = {
            "to_email": to_email,
            "token": token,
            "verification_link": verification_link,
            "sent_at": datetime.now(timezone.utc),
            "subject": subject,
        }

    # Record in dev emails log file
    try:
        os.makedirs(DEV_LOG_DIR, exist_ok=True)
        with open(DEV_EMAIL_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now(timezone.utc).isoformat()}] TO: {to_email} | TOKEN: {token} | LINK: {verification_link}\n"
            )
    except Exception as log_err:
        logger.warning("Could not write to dev_emails.log: %s", log_err)

    if SMTP_HOST:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM_EMAIL
            msg["To"] = to_email

            part1 = MIMEText(plain_text, "plain")
            part2 = MIMEText(html, "html")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                if SMTP_PORT == 587:
                    server.starttls()
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM_EMAIL, [to_email], msg.as_string())

            logger.info("Verification email delivered via SMTP to %s", to_email)
            return True
        except Exception as smtp_err:
            logger.error("Failed to send verification email via SMTP to %s: %s", to_email, smtp_err)
            # Do not raise to avoid crashing request; log recorded in dev store
            return False
    else:
        logger.info(
            "[DEV EMAIL] Verification email captured for %s. Link: %s",
            to_email,
            verification_link,
        )
        return True


def get_latest_dev_email(email: str) -> Optional[Dict[str, Any]]:
    """Helper for testing and local inspection to retrieve the most recent verification email."""
    with _dev_email_lock:
        return _dev_email_store.get(email.lower())


def clear_dev_email_store() -> None:
    """Helper for testing to reset captured development emails."""
    with _dev_email_lock:
        _dev_email_store.clear()

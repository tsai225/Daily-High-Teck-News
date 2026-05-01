"""
src/sender.py — Send email via Gmail SMTP (STARTTLS on port 587).

Reads configuration from environment variables:
  Required:
    SMTP_USERNAME  — Gmail address used for authentication
    SMTP_PASSWORD  — Gmail App Password
    MAIL_TO        — recipient(s), comma-separated

  Optional:
    MAIL_FROM      — sender display address (defaults to SMTP_USERNAME)
    MAIL_CC        — CC recipients, comma-separated
    SMTP_HOST      — defaults to smtp.gmail.com
    SMTP_PORT      — defaults to 587
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set or empty.")
    return value


def send_email(
    subject: str,
    html_body: str,
    plain_body: str,
) -> None:
    """
    Send a multipart/alternative email (HTML + plain text).

    Raises:
        EnvironmentError: if required env vars are missing.
        smtplib.SMTPException: on SMTP errors.
    """
    smtp_user = _get_required_env("SMTP_USERNAME")
    smtp_pass = _get_required_env("SMTP_PASSWORD")
    mail_to_raw = _get_required_env("MAIL_TO")
    mail_from = os.environ.get("MAIL_FROM", smtp_user).strip() or smtp_user
    mail_cc_raw = os.environ.get("MAIL_CC", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    to_addrs = [a.strip() for a in mail_to_raw.split(",") if a.strip()]
    cc_addrs = [a.strip() for a in mail_cc_raw.split(",") if a.strip()] if mail_cc_raw else []
    all_recipients = to_addrs + cc_addrs

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("Connecting to %s:%d …", smtp_host, smtp_port)
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, all_recipients, msg.as_string())
    logger.info("Email sent to %s", ", ".join(all_recipients))

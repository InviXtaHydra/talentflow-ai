"""Outgoing e-mail. Development uses Mailpit (an SMTP catcher with a web inbox); tests use an in-memory outbox.
E-mail bodies contain one-time links and are never logged."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("talentflow.email")


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str


outbox: list[OutgoingEmail] = []


def send_email(message: OutgoingEmail) -> bool:
    settings = get_settings()
    if settings.email_backend == "memory":
        outbox.append(message)
        return True
    if settings.email_backend == "console":
        logger.info("E-mail '%s' not sent (EMAIL_BACKEND=console)", message.subject)
        return True
    mail = EmailMessage()
    mail["From"] = settings.email_from
    mail["To"] = message.to
    mail["Subject"] = message.subject
    mail.set_content(message.text)
    mail.add_alternative(message.html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(mail)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        logger.error("Sending e-mail '%s' failed: %s", message.subject, type(exc).__name__)
        return False

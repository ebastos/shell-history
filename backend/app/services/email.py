"""Email sending service using SMTP"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> None:
    """Send an email via SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML email body
        text_body: Optional plain text email body (defaults to HTML stripped)

    Raises:
        smtplib.SMTPException: If email sending fails
        ValueError: If SMTP configuration is incomplete
    """
    # Validate SMTP configuration
    if not settings.smtp_host:
        raise ValueError("SMTP_HOST not configured")

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    # Add text and HTML parts
    if text_body:
        text_part = MIMEText(text_body, "plain")
        msg.attach(text_part)

    html_part = MIMEText(html_body, "html")
    msg.attach(html_part)

    # Send email
    try:
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise smtplib.SMTPException(f"Failed to send email: {str(e)}") from e

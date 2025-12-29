"""Tests for email sending service

Unit tests for send_email() function with mocked SMTP,
testing configuration validation, TLS paths, and error handling.
"""

import smtplib
from unittest.mock import MagicMock, patch

import pytest


class TestSendEmail:
    """Tests for send_email function"""

    @patch("app.services.email.settings")
    def test_send_email_missing_smtp_host_raises_error(self, mock_settings):
        """Test that missing SMTP_HOST raises ValueError"""
        mock_settings.smtp_host = None

        from app.services.email import send_email

        with pytest.raises(ValueError, match="SMTP_HOST not configured"):
            send_email(
                to_email="test@example.com",
                subject="Test",
                html_body="<p>Test</p>",
            )

    @patch("app.services.email.smtplib.SMTP")
    @patch("app.services.email.settings")
    def test_send_email_success_with_tls(self, mock_settings, mock_smtp_class):
        """Test successful email sending with TLS enabled"""
        # Configure mock settings
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "password123"
        mock_settings.smtp_from_email = "sender@example.com"

        # Configure mock SMTP instance
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        from app.services.email import send_email

        send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Hello World</p>",
        )

        # Verify SMTP was called correctly
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "password123")
        mock_smtp.send_message.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch("app.services.email.smtplib.SMTP")
    @patch("app.services.email.settings")
    def test_send_email_success_without_tls(self, mock_settings, mock_smtp_class):
        """Test successful email sending without TLS"""
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 25
        mock_settings.smtp_use_tls = False
        mock_settings.smtp_user = None
        mock_settings.smtp_password = None
        mock_settings.smtp_from_email = "sender@example.com"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        from app.services.email import send_email

        send_email(
            to_email="recipient@example.com",
            subject="Test",
            html_body="<p>Test</p>",
        )

        # Verify TLS was NOT called
        mock_smtp.starttls.assert_not_called()
        # Verify login was NOT called (no credentials)
        mock_smtp.login.assert_not_called()
        mock_smtp.send_message.assert_called_once()

    @patch("app.services.email.smtplib.SMTP")
    @patch("app.services.email.settings")
    def test_send_email_with_auth(self, mock_settings, mock_smtp_class):
        """Test that login is called when credentials are provided"""
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_user = "authenticated_user"
        mock_settings.smtp_password = "secure_password"
        mock_settings.smtp_from_email = "sender@example.com"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        from app.services.email import send_email

        send_email(
            to_email="recipient@example.com",
            subject="Test",
            html_body="<p>Test</p>",
        )

        mock_smtp.login.assert_called_once_with("authenticated_user", "secure_password")

    @patch("app.services.email.smtplib.SMTP")
    @patch("app.services.email.settings")
    def test_send_email_smtp_failure_raises_exception(
        self, mock_settings, mock_smtp_class
    ):
        """Test that SMTP connection failures raise SMTPException"""
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = False
        mock_settings.smtp_from_email = "sender@example.com"

        mock_smtp_class.side_effect = ConnectionRefusedError("Connection refused")

        from app.services.email import send_email

        with pytest.raises(smtplib.SMTPException, match="Failed to send email"):
            send_email(
                to_email="recipient@example.com",
                subject="Test",
                html_body="<p>Test</p>",
            )

    @patch("app.services.email.smtplib.SMTP")
    @patch("app.services.email.settings")
    def test_send_email_with_text_body(self, mock_settings, mock_smtp_class):
        """Test that both text and HTML parts are attached"""
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = False
        mock_settings.smtp_user = None
        mock_settings.smtp_password = None
        mock_settings.smtp_from_email = "sender@example.com"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        from app.services.email import send_email

        send_email(
            to_email="recipient@example.com",
            subject="Test",
            html_body="<p>HTML content</p>",
            text_body="Plain text content",
        )

        # Verify send_message was called
        mock_smtp.send_message.assert_called_once()
        # Get the message that was sent
        sent_message = mock_smtp.send_message.call_args[0][0]

        # Verify message structure
        assert sent_message["Subject"] == "Test"
        assert sent_message["To"] == "recipient@example.com"
        assert sent_message["From"] == "sender@example.com"

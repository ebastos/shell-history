"""Tests for session management service

Unit tests for SessionManager class covering token creation,
verification, expiration, and error handling.
"""

from unittest.mock import patch
from uuid import UUID, uuid4

from app.services.session import SessionManager


class TestSessionManager:
    """Tests for SessionManager class"""

    def setup_method(self):
        """Create a fresh SessionManager for each test"""
        self.secret_key = "test-secret-key-for-testing"
        self.manager = SessionManager(self.secret_key)

    def test_create_session_returns_signed_token(self):
        """Test that create_session returns a valid signed token string"""
        user_id = uuid4()
        token = self.manager.create_session(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        # Token should contain the user_id (signed)
        assert "." in token  # Signed tokens have a signature separator

    def test_verify_session_valid_token(self):
        """Test round-trip: create -> verify returns same UUID"""
        user_id = uuid4()
        token = self.manager.create_session(user_id)

        verified_id = self.manager.verify_session(token)

        assert verified_id is not None
        assert verified_id == user_id

    def test_verify_session_expired_token(self):
        """Test that expired tokens return None"""
        user_id = uuid4()
        token = self.manager.create_session(user_id)

        # Mock time to be beyond expiration (default is 24 hours)
        with patch("app.services.session.TimestampSigner.unsign") as mock_unsign:
            from itsdangerous import SignatureExpired

            mock_unsign.side_effect = SignatureExpired("Signature expired")

            verified_id = self.manager.verify_session(token)
            assert verified_id is None

    def test_verify_session_invalid_signature(self):
        """Test that tampered tokens return None"""
        user_id = uuid4()
        token = self.manager.create_session(user_id)

        # Tamper with the token by changing characters
        tampered_token = token[:-5] + "XXXXX"

        verified_id = self.manager.verify_session(tampered_token)
        assert verified_id is None

    def test_verify_session_malformed_token(self):
        """Test that random garbage returns None"""
        garbage_tokens = [
            "not-a-valid-token",
            "",
            "random-garbage-string",
            "12345",
            "a.b.c.d.e.f",
        ]

        for garbage in garbage_tokens:
            verified_id = self.manager.verify_session(garbage)
            assert verified_id is None, f"Expected None for garbage token: {garbage}"

    def test_verify_session_wrong_secret(self):
        """Test that tokens signed with different key fail verification"""
        user_id = uuid4()

        # Create token with one secret
        manager1 = SessionManager("secret-key-one")
        token = manager1.create_session(user_id)

        # Try to verify with different secret
        manager2 = SessionManager("secret-key-two")
        verified_id = manager2.verify_session(token)

        assert verified_id is None

    def test_session_manager_uses_configured_expire_hours(self):
        """Test that session manager respects expire_hours setting"""
        with patch("app.services.session.settings") as mock_settings:
            mock_settings.secret_key = "test-key"
            mock_settings.session_expire_hours = 48

            manager = SessionManager("test-key")
            assert manager.expire_hours == 48


class TestSessionManagerEdgeCases:
    """Edge case tests for SessionManager"""

    def test_create_session_with_specific_uuid(self):
        """Test creating session with a known UUID"""
        manager = SessionManager("test-secret")
        known_uuid = UUID("12345678-1234-5678-1234-567812345678")

        token = manager.create_session(known_uuid)
        verified = manager.verify_session(token)

        assert verified == known_uuid

    def test_multiple_sessions_same_user(self):
        """Test that multiple sessions can be created for same user"""
        manager = SessionManager("test-secret")
        user_id = uuid4()

        token1 = manager.create_session(user_id)
        token2 = manager.create_session(user_id)

        # Tokens should be different (different timestamps)
        # But both should verify to the same user
        assert manager.verify_session(token1) == user_id
        assert manager.verify_session(token2) == user_id

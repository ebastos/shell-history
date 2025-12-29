"""Pytest configuration and shared fixtures"""

import secrets

import pytest
from app.models import ApiKey, User
from app.services.api_key import hash_api_key
from app.services.csrf import csrf_service


@pytest.fixture
def test_user_factory():
    """Factory to create test users - call with db_session"""

    def _create_user(db_session, username="testuser", email="test@example.com"):
        user = User(
            username=username,
            email=email,
            role="user",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create API key for the user (hashed)
        api_key_value = secrets.token_urlsafe(32)
        hashed_key = hash_api_key(api_key_value)
        api_key = ApiKey(
            user_id=user.id,
            key=hashed_key,
            is_active=True,
        )
        db_session.add(api_key)
        db_session.commit()
        db_session.refresh(user)
        # Store plaintext key for test use
        user._plaintext_api_key = api_key_value
        return user

    return _create_user


def create_auth_headers(user: User, db_session=None) -> dict[str, str]:
    """Helper function to create auth headers from a user.

    Note: User must have _plaintext_api_key attribute set (from test_user_factory).
    """
    # Use the plaintext key stored on the user object
    plaintext_key = getattr(user, "_plaintext_api_key", None)
    if plaintext_key:
        return {"X-API-Key": plaintext_key}
    return {"X-API-Key": ""}


def get_csrf_token() -> str:
    """Generate a valid CSRF token for testing"""
    return csrf_service.generate_token()

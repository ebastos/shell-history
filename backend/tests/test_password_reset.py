"""Tests for password reset functionality"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import PasswordResetToken, User
from app.services.password import hash_password, verify_password
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.conftest import get_csrf_token

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    # Setup dependency override
    app.dependency_overrides[get_db] = override_get_db

    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Get a database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user_with_password(db_session):
    """Create a test user with password"""
    password_hash = hash_password("testpass123")
    user = User(
        username="testuser",
        email="test@example.com",
        role="user",
        password_hash=password_hash,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_forgot_password_page():
    """Test accessing forgot password page"""
    response = client.get("/forgot-password")
    assert response.status_code == 200
    assert "Forgot Password" in response.text
    assert "email" in response.text


def test_forgot_password_request_success(test_user_with_password):
    """Test successful password reset request"""
    with patch("app.routers.user_ui.send_email") as mock_send:
        response = client.post(
            "/forgot-password",
            data={"email": "test@example.com", "csrf_token": get_csrf_token()},
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "password reset link" in response.text.lower()
        # Verify email was sent
        mock_send.assert_called_once()
        # Verify token was created
        db = TestingSessionLocal()
        try:
            token = (
                db.query(PasswordResetToken)
                .filter(PasswordResetToken.user_id == test_user_with_password.id)
                .first()
            )
            assert token is not None
            assert token.used_at is None
            assert token.expires_at > datetime.utcnow()
        finally:
            db.close()


def test_forgot_password_nonexistent_email():
    """Test password reset request with nonexistent email"""
    with patch("app.routers.user_ui.send_email") as mock_send:
        response = client.post(
            "/forgot-password",
            data={"email": "nonexistent@example.com", "csrf_token": get_csrf_token()},
        )
        # Should still return success (security: don't reveal if email exists)
        assert response.status_code == 200
        # But email should not be sent
        mock_send.assert_not_called()


def test_forgot_password_inactive_user(db_session):
    """Test password reset request for inactive user"""
    password_hash = hash_password("testpass123")
    user = User(
        username="inactive",
        email="inactive@example.com",
        role="user",
        password_hash=password_hash,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    with patch("app.routers.user_ui.send_email") as mock_send:
        response = client.post(
            "/forgot-password",
            data={"email": "inactive@example.com", "csrf_token": get_csrf_token()},
        )
        # Should still return success (security)
        assert response.status_code == 200
        # But email should not be sent
        mock_send.assert_not_called()


def test_reset_password_page_invalid_token():
    """Test accessing reset password page with invalid token"""
    response = client.get("/reset-password?token=invalid-token")
    assert response.status_code == 400
    assert "invalid" in response.text.lower() or "expired" in response.text.lower()


def test_reset_password_page_valid_token(test_user_with_password, db_session):
    """Test accessing reset password page with valid token"""
    # Create a valid token
    token_value = "valid-reset-token-123"
    reset_token = PasswordResetToken(
        user_id=test_user_with_password.id,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.get(f"/reset-password?token={token_value}")
    assert response.status_code == 200
    assert "Reset Password" in response.text
    assert "password" in response.text


def test_reset_password_success(test_user_with_password, db_session):
    """Test successful password reset"""
    # Create a valid token
    token_value = "valid-reset-token-123"
    reset_token = PasswordResetToken(
        user_id=test_user_with_password.id,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add(reset_token)
    db_session.commit()

    # Reset password
    response = client.post(
        "/reset-password",
        data={
            "token": token_value,
            "password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?reset=success"

    # Verify password was changed
    db_session.refresh(test_user_with_password)
    assert verify_password("newpassword123", test_user_with_password.password_hash)
    assert not verify_password("testpass123", test_user_with_password.password_hash)

    # Verify token was marked as used
    db_session.refresh(reset_token)
    assert reset_token.used_at is not None


def test_reset_password_invalid_token():
    """Test password reset with invalid token"""
    response = client.post(
        "/reset-password",
        data={
            "token": "invalid-token",
            "password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 400
    assert "invalid" in response.text.lower() or "expired" in response.text.lower()


def test_reset_password_expired_token(test_user_with_password, db_session):
    """Test password reset with expired token"""
    # Create an expired token
    token_value = "expired-token-123"
    reset_token = PasswordResetToken(
        user_id=test_user_with_password.id,
        token=token_value,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        "/reset-password",
        data={
            "token": token_value,
            "password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 400
    assert "expired" in response.text.lower()


def test_reset_password_used_token(test_user_with_password, db_session):
    """Test password reset with already used token"""
    # Create a used token
    token_value = "used-token-123"
    reset_token = PasswordResetToken(
        user_id=test_user_with_password.id,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        used_at=datetime.utcnow() - timedelta(minutes=5),
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        "/reset-password",
        data={
            "token": token_value,
            "password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 400
    assert "already used" in response.text.lower() or "invalid" in response.text.lower()


def test_reset_password_weak_password(test_user_with_password, db_session):
    """Test password reset with weak password"""
    token_value = "valid-token-123"
    reset_token = PasswordResetToken(
        user_id=test_user_with_password.id,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add(reset_token)
    db_session.commit()

    # Try with very short password
    response = client.post(
        "/reset-password",
        data={"token": token_value, "password": "123", "csrf_token": get_csrf_token()},
    )
    # Should validate minimum length (assuming we add validation)
    # For now, just check it doesn't crash
    assert response.status_code in [400, 422]

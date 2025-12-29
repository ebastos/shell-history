"""Tests for email change functionality"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import EmailVerificationToken, User
from app.services.password import hash_password
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


@pytest.fixture
def authenticated_session(test_user_with_password):
    """Create an authenticated session"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(test_user_with_password.id)
    return session_token


def test_change_email_requires_auth():
    """Test that change email requires authentication"""
    response = client.post(
        "/account/change-email",
        data={
            "new_email": "new@example.com",
            "password": "testpass123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 401


def test_change_email_success(test_user_with_password, authenticated_session):
    """Test successful email change request"""
    with patch("app.routers.user_ui.send_email") as mock_send:
        response = client.post(
            "/account/change-email",
            data={
                "new_email": "newemail@example.com",
                "password": "testpass123",
                "csrf_token": get_csrf_token(),
            },
            cookies={"session": authenticated_session},
        )
        assert response.status_code == 200
        # Verify email was sent to new address
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["to_email"] == "newemail@example.com"

        # Verify token was created
        db = TestingSessionLocal()
        try:
            token = (
                db.query(EmailVerificationToken)
                .filter(EmailVerificationToken.user_id == test_user_with_password.id)
                .first()
            )
            assert token is not None
            assert token.new_email == "newemail@example.com"
            assert token.used_at is None
            assert token.expires_at > datetime.utcnow()
        finally:
            db.close()


def test_change_email_wrong_password(test_user_with_password, authenticated_session):
    """Test email change with wrong password"""
    response = client.post(
        "/account/change-email",
        data={
            "new_email": "newemail@example.com",
            "password": "wrongpassword",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 400
    assert "password" in response.text.lower()

    # Verify email was not changed
    db = TestingSessionLocal()
    try:
        # Refresh from a new session to be safe
        user = db.query(User).filter(User.id == test_user_with_password.id).first()
        assert user.email == "test@example.com"
    finally:
        db.close()


def test_change_email_duplicate_email(
    test_user_with_password, authenticated_session, db_session
):
    """Test email change to an email that already exists"""
    # Create another user with the target email
    password_hash = hash_password("otherpass")
    other_user = User(
        username="otheruser",
        email="newemail@example.com",
        role="user",
        password_hash=password_hash,
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    response = client.post(
        "/account/change-email",
        data={
            "new_email": "newemail@example.com",
            "password": "testpass123",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 400
    assert "already" in response.text.lower() or "exists" in response.text.lower()


def test_verify_email_success(test_user_with_password, db_session):
    """Test successful email verification"""
    # Create a valid token
    token_value = "valid-verification-token-123"
    verification_token = EmailVerificationToken(
        user_id=test_user_with_password.id,
        new_email="newemail@example.com",
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add(verification_token)
    db_session.commit()

    # Verify email
    response = client.get(f"/verify-email?token={token_value}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/account?email_verified=true"

    # Verify email was changed
    db_session.refresh(test_user_with_password)
    assert test_user_with_password.email == "newemail@example.com"

    # Verify token was marked as used
    db_session.refresh(verification_token)
    assert verification_token.used_at is not None


def test_verify_email_invalid_token():
    """Test email verification with invalid token"""
    response = client.get("/verify-email?token=invalid-token")
    assert response.status_code == 400
    assert "invalid" in response.text.lower() or "expired" in response.text.lower()


def test_verify_email_expired_token(test_user_with_password, db_session):
    """Test email verification with expired token"""
    token_value = "expired-token-123"
    verification_token = EmailVerificationToken(
        user_id=test_user_with_password.id,
        new_email="newemail@example.com",
        token=token_value,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(verification_token)
    db_session.commit()

    response = client.get(f"/verify-email?token={token_value}")
    assert response.status_code == 400
    assert "expired" in response.text.lower()


def test_verify_email_used_token(test_user_with_password, db_session):
    """Test email verification with already used token"""
    token_value = "used-token-123"
    verification_token = EmailVerificationToken(
        user_id=test_user_with_password.id,
        new_email="newemail@example.com",
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        used_at=datetime.utcnow() - timedelta(minutes=5),
    )
    db_session.add(verification_token)
    db_session.commit()

    response = client.get(f"/verify-email?token={token_value}")
    assert response.status_code == 400
    assert "already used" in response.text.lower() or "invalid" in response.text.lower()

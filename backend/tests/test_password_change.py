"""Tests for password change functionality"""

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import User
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
def test_user(db_session):
    """Create a test user"""
    password_hash = hash_password("oldpassword")
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
def authenticated_session(test_user):
    """Create an authenticated session"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(test_user.id)
    return session_token


def test_change_password_requires_auth():
    """Test that change password requires authentication"""
    response = client.post(
        "/account/change-password",
        data={
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 401


def test_change_password_success(test_user, authenticated_session, db_session):
    """Test successful password change"""
    response = client.post(
        "/account/change-password",
        data={
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 200
    assert "success" in response.text.lower()
    assert "updated successfully" in response.text.lower()

    # Verify password was updated in DB
    db_session.refresh(test_user)
    assert verify_password("newpassword123", test_user.password_hash)
    assert not verify_password("oldpassword", test_user.password_hash)


def test_change_password_wrong_current_password(
    test_user, authenticated_session, db_session
):
    """Test password change with wrong current password"""
    response = client.post(
        "/account/change-password",
        data={
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 400
    assert "invalid" in response.text.lower()

    # Verify password was not changed
    db_session.refresh(test_user)
    assert verify_password("oldpassword", test_user.password_hash)


def test_change_password_mismatched_new_passwords(
    test_user, authenticated_session, db_session
):
    """Test password change with mismatched new passwords"""
    response = client.post(
        "/account/change-password",
        data={
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "confirm_password": "mismatch",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 400
    assert "match" in response.text.lower()

    # Verify password was not changed
    db_session.refresh(test_user)
    assert verify_password("oldpassword", test_user.password_hash)


def test_change_password_too_short(test_user, authenticated_session, db_session):
    """Test password change with too short new password"""
    response = client.post(
        "/account/change-password",
        data={
            "current_password": "oldpassword",
            "new_password": "short",
            "confirm_password": "short",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 400
    assert "least 8 characters" in response.text.lower()

    # Verify password was not changed
    db_session.refresh(test_user)
    assert verify_password("oldpassword", test_user.password_hash)

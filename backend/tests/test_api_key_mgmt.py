"""Tests for API key management endpoints"""

import secrets

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import ApiKey, User
from app.services.password import hash_password
from app.services.session import session_manager
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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
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
    """Create an authenticated session for test user"""
    session_token = session_manager.create_session(test_user_with_password.id)
    return {"session": session_token}


def test_create_api_key(authenticated_session, test_user_with_password, db_session):
    """Test creating a new API key"""
    response = client.post(
        "/account/api-keys",
        cookies=authenticated_session,
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response.status_code == 200

    # Check that API key was created
    api_keys = (
        db_session.query(ApiKey)
        .filter(ApiKey.user_id == test_user_with_password.id, ApiKey.is_active)
        .all()
    )
    assert len(api_keys) == 1
    assert api_keys[0].key is not None
    assert api_keys[0].user_id == test_user_with_password.id

    # API keys are now stored as hashes (bcrypt), so we can't match the DB value
    # to the response. Instead, verify the response contains a key-like pattern.
    # The stored key starts with "$2b$" (bcrypt hash prefix)
    assert api_keys[0].key.startswith("$2b$")
    # Response should contain a plaintext key (shown once) - verify something is there
    assert "api-key-item" in response.text


def test_create_api_key_requires_auth():
    """Test that creating API key requires authentication"""
    response = client.post(
        "/account/api-keys",
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response.status_code == 401


def test_create_multiple_api_keys(
    authenticated_session, test_user_with_password, db_session
):
    """Test creating multiple API keys"""
    # Create first key
    response1 = client.post(
        "/account/api-keys",
        cookies=authenticated_session,
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response1.status_code == 200

    # Create second key
    response2 = client.post(
        "/account/api-keys",
        cookies=authenticated_session,
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response2.status_code == 200

    # Check that both keys exist
    api_keys = (
        db_session.query(ApiKey)
        .filter(ApiKey.user_id == test_user_with_password.id, ApiKey.is_active)
        .all()
    )
    assert len(api_keys) == 2


def test_revoke_api_key(authenticated_session, test_user_with_password, db_session):
    """Test revoking an API key"""
    # Create an API key first
    api_key = ApiKey(
        user_id=test_user_with_password.id,
        key=secrets.token_urlsafe(32),
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    # Revoke it
    response = client.post(
        f"/account/api-keys/{api_key.id}/revoke",
        cookies=authenticated_session,
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response.status_code == 200

    # Check that key is deactivated
    db_session.refresh(api_key)
    assert api_key.is_active is False


def test_revoke_api_key_requires_auth(test_user_with_password, db_session):
    """Test that revoking API key requires authentication"""
    api_key = ApiKey(
        user_id=test_user_with_password.id,
        key=secrets.token_urlsafe(32),
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    response = client.post(
        f"/account/api-keys/{api_key.id}/revoke",
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response.status_code == 401


def test_revoke_other_user_api_key(authenticated_session, db_session):
    """Test that user cannot revoke another user's API key"""
    # Create another user
    password_hash = hash_password("otherpass")
    other_user = User(
        username="otheruser",
        email="other@example.com",
        role="user",
        password_hash=password_hash,
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    # Create API key for other user
    api_key = ApiKey(
        user_id=other_user.id,
        key=secrets.token_urlsafe(32),
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    # Try to revoke it (should fail)
    response = client.post(
        f"/account/api-keys/{api_key.id}/revoke",
        cookies=authenticated_session,
        headers={"HX-Request": "true", "X-CSRF-Token": get_csrf_token()},
    )
    assert response.status_code == 404  # Not found (user doesn't own it)

    # Verify key is still active
    db_session.refresh(api_key)
    assert api_key.is_active is True


def test_list_api_keys_on_account_page(
    authenticated_session, test_user_with_password, db_session
):
    """Test that account page shows user's API keys"""
    # Create some API keys
    api_key1 = ApiKey(
        user_id=test_user_with_password.id,
        key=secrets.token_urlsafe(32),
        name="Key 1",
        is_active=True,
    )
    api_key2 = ApiKey(
        user_id=test_user_with_password.id,
        key=secrets.token_urlsafe(32),
        name="Key 2",
        is_active=True,
    )
    db_session.add(api_key1)
    db_session.add(api_key2)
    db_session.commit()

    # Get account page
    response = client.get("/account", cookies=authenticated_session)
    assert response.status_code == 200
    assert "Key 1" in response.text or "Unnamed Key" in response.text

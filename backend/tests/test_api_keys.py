"""Tests for ApiKey model"""

import secrets
from datetime import datetime

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import ApiKey, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
def test_user(db_session):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_api_key(db_session, test_user):
    """Test creating an API key"""
    api_key = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
        name="Test Key",
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.id is not None
    assert api_key.user_id == test_user.id
    assert api_key.key is not None
    assert api_key.name == "Test Key"
    assert api_key.is_active is True
    assert api_key.created_at is not None
    assert api_key.last_used_at is None


def test_api_key_user_relationship(db_session, test_user):
    """Test that API key has relationship to user"""
    api_key = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.user is not None
    assert api_key.user.id == test_user.id
    assert api_key.user.username == "testuser"


def test_user_api_keys_relationship(db_session, test_user):
    """Test that user has relationship to API keys"""
    api_key1 = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
        name="Key 1",
    )
    api_key2 = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
        name="Key 2",
    )
    db_session.add(api_key1)
    db_session.add(api_key2)
    db_session.commit()
    db_session.refresh(test_user)

    assert len(test_user.api_keys) == 2
    assert api_key1 in test_user.api_keys
    assert api_key2 in test_user.api_keys


def test_api_key_unique_constraint(db_session, test_user):
    """Test that API keys must be unique"""
    key_value = secrets.token_urlsafe(32)
    api_key1 = ApiKey(
        user_id=test_user.id,
        key=key_value,
    )
    db_session.add(api_key1)
    db_session.commit()

    # Try to create another API key with the same key value
    api_key2 = ApiKey(
        user_id=test_user.id,
        key=key_value,
    )
    db_session.add(api_key2)
    with pytest.raises(Exception):  # Should raise IntegrityError
        db_session.commit()


def test_api_key_last_used_at(db_session, test_user):
    """Test updating last_used_at timestamp"""
    api_key = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.last_used_at is None

    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.last_used_at is not None


def test_api_key_deactivate(db_session, test_user):
    """Test deactivating an API key"""
    api_key = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.is_active is True

    # Deactivate
    api_key.is_active = False
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.is_active is False


def test_api_key_optional_name(db_session, test_user):
    """Test that API key name is optional"""
    api_key = ApiKey(
        user_id=test_user.id,
        key=secrets.token_urlsafe(32),
        name=None,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    assert api_key.name is None

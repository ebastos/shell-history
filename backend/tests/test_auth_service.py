"""Tests for auth service with ApiKey model"""

import secrets
from typing import Any

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import ApiKey, User
from app.services.api_key import hash_api_key
from app.services.auth import get_current_user
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.asyncio

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


@pytest.fixture
def test_api_key(db_session, test_user):
    """Create a test API key with hashed storage"""
    # Generate plaintext key
    plaintext_key = secrets.token_urlsafe(32)
    # Hash it for storage
    hashed_key = hash_api_key(plaintext_key)

    api_key = ApiKey(
        user_id=test_user.id,
        key=hashed_key,
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    # Store plaintext for test use
    api_key._plaintext_key = plaintext_key
    return api_key


async def test_get_current_user_with_api_key(db_session, test_user, test_api_key):
    """Test getting current user via API key"""
    # Get the plaintext key stored on the fixture
    plaintext_key = test_api_key._plaintext_key

    # Create a mock request with API key header
    class MockRequest:
        def __init__(self, api_key: str) -> None:
            self.cookies: dict[str, str] = {}
            self.headers: dict[str, str] = {"x-api-key": api_key}

    request: Any = MockRequest(plaintext_key)

    # Get user via dependency
    user = await get_current_user(
        request=request,
        x_api_key=plaintext_key,
        db=db_session,
    )

    assert user is not None
    assert user.id == test_user.id
    assert user.username == "testuser"


async def test_get_current_user_with_invalid_api_key(db_session):
    """Test that invalid API key raises 401"""

    class MockRequest:
        def __init__(self) -> None:
            self.cookies: dict[str, str] = {}
            self.headers: dict[str, str] = {}

    request: Any = MockRequest()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            request=request,
            x_api_key="invalid-key",
            db=db_session,
        )
    assert exc_info.value.status_code == 401


async def test_get_current_user_with_inactive_api_key(
    db_session, test_user, test_api_key
):
    """Test that inactive API key raises 401"""
    # Deactivate the API key
    test_api_key.is_active = False
    db_session.commit()

    # Get the plaintext key stored on the fixture
    plaintext_key = test_api_key._plaintext_key

    class MockRequest:
        def __init__(self) -> None:
            self.cookies: dict[str, str] = {}
            self.headers: dict[str, str] = {}

    request: Any = MockRequest()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            request=request,
            x_api_key=plaintext_key,
            db=db_session,
        )
    assert exc_info.value.status_code == 401


async def test_get_current_user_updates_last_used_at(
    db_session, test_user, test_api_key
):
    """Test that API key last_used_at is updated on authentication"""
    assert test_api_key.last_used_at is None

    # Get the plaintext key stored on the fixture
    plaintext_key = test_api_key._plaintext_key

    class MockRequest:
        def __init__(self, api_key: str) -> None:
            self.cookies: dict[str, str] = {}
            self.headers: dict[str, str] = {"x-api-key": api_key}

    request: Any = MockRequest(plaintext_key)

    await get_current_user(
        request=request,
        x_api_key=plaintext_key,
        db=db_session,
    )

    # Refresh from database
    db_session.refresh(test_api_key)
    assert test_api_key.last_used_at is not None


async def test_get_current_user_with_session(db_session, test_user):
    """Test getting current user via session cookie"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(test_user.id)

    class MockRequest:
        def __init__(self, session: str) -> None:
            self.cookies: dict[str, str] = {"session": session}
            self.headers: dict[str, str] = {}

    request: Any = MockRequest(session_token)

    user = await get_current_user(
        request=request,
        x_api_key=None,
        db=db_session,
    )

    assert user is not None
    assert user.id == test_user.id


async def test_get_current_user_no_auth(db_session):
    """Test that missing auth raises 401"""

    class MockRequest:
        def __init__(self) -> None:
            self.cookies: dict[str, str] = {}
            self.headers: dict[str, str] = {}

    request: Any = MockRequest()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            request=request,
            x_api_key=None,
            db=db_session,
        )
    assert exc_info.value.status_code == 401

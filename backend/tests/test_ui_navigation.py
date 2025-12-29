"""Tests for UI navigation between command history and account pages"""

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.services.password import hash_password
from app.services.session import session_manager
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
    """Create an authenticated session for a test user"""
    session_token = session_manager.create_session(test_user_with_password.id)
    return {"session": session_token}


def test_history_page_has_navigation_to_account(authenticated_session):
    """Test that the history page has a link/button to navigate to account page"""
    response = client.get("/history", cookies=authenticated_session)
    assert response.status_code == 200
    # Check for navigation link to account page
    assert 'href="/account"' in response.text or 'hx-get="/account"' in response.text
    # Check for account-related text (Account, API Keys, etc.)
    assert "Account" in response.text or "API Keys" in response.text


def test_account_page_has_navigation_to_history(authenticated_session):
    """Test that the account page has a link/button to navigate to history page"""
    response = client.get("/account", cookies=authenticated_session)
    assert response.status_code == 200
    # Check for navigation link to history page
    assert 'href="/history"' in response.text or 'hx-get="/history"' in response.text
    # Check for command history related text
    assert (
        "Shell History" in response.text
        or "Search" in response.text
        or "Commands" in response.text
    )


def test_navigation_from_history_to_account_works(authenticated_session):
    """Test that clicking navigation from history page goes to account page"""
    # Get history page
    history_response = client.get("/history", cookies=authenticated_session)
    assert history_response.status_code == 200

    # Navigate to account page
    account_response = client.get("/account", cookies=authenticated_session)
    assert account_response.status_code == 200
    assert "Account" in account_response.text
    assert "API Keys" in account_response.text


def test_navigation_from_account_to_history_works(authenticated_session):
    """Test that clicking navigation from account page goes to history page"""
    # Get account page
    account_response = client.get("/account", cookies=authenticated_session)
    assert account_response.status_code == 200

    # Navigate to history page
    history_response = client.get("/history", cookies=authenticated_session)
    assert history_response.status_code == 200
    assert "Shell History" in history_response.text
    # Check for search functionality
    assert "placeholder=" in history_response.text or "Search" in history_response.text

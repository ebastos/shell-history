"""Tests for user authentication (login/logout)"""

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import User
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


def test_login_page():
    """Test accessing login page"""
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text
    assert "username" in response.text
    assert "password" in response.text


def test_login_success(test_user_with_password):
    """Test successful login"""
    response = client.post(
        "/login",
        data={
            "username": "testuser",
            "password": "testpass123",
            "csrf_token": get_csrf_token(),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/account"
    # Check that session cookie is set
    assert "session" in response.cookies


def test_login_invalid_username():
    """Test login with invalid username"""
    response = client.post(
        "/login",
        data={
            "username": "nonexistent",
            "password": "testpass123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_login_invalid_password(test_user_with_password):
    """Test login with invalid password"""
    response = client.post(
        "/login",
        data={
            "username": "testuser",
            "password": "wrongpassword",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_login_inactive_user(db_session):
    """Test login with inactive user"""
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

    response = client.post(
        "/login",
        data={
            "username": "inactive",
            "password": "testpass123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 403
    assert "Account is inactive" in response.text


def test_logout(test_user_with_password):
    """Test logout"""
    # First login to get a session
    login_response = client.post(
        "/login",
        data={
            "username": "testuser",
            "password": "testpass123",
            "csrf_token": get_csrf_token(),
        },
        follow_redirects=False,
    )
    session_cookie = login_response.cookies.get("session")

    # Now logout
    response = client.post(
        "/logout",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_cookie},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    # Check that session cookie is deleted
    assert "session" not in response.cookies or response.cookies["session"] == ""


def test_account_requires_auth():
    """Test that account page requires authentication"""
    response = client.get("/account", follow_redirects=False)
    assert response.status_code == 401


def test_account_with_session(test_user_with_password):
    """Test accessing account page with valid session"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(test_user_with_password.id)
    response = client.get("/account", cookies={"session": session_token})
    assert response.status_code == 200
    assert "testuser" in response.text
    assert "Account" in response.text
    assert "API Keys" in response.text


def test_account_shows_user_info(test_user_with_password):
    """Test that account page shows user information"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(test_user_with_password.id)
    response = client.get("/account", cookies={"session": session_token})
    assert response.status_code == 200
    assert test_user_with_password.username in response.text
    assert test_user_with_password.email in response.text
    assert test_user_with_password.role in response.text

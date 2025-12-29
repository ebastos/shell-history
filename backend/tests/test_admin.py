"""Tests for admin interface"""

from uuid import uuid4

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import User
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
def admin_user():
    """Create an admin user with password for testing"""
    db = TestingSessionLocal()
    try:
        # Import here to trigger lazy initialization after test setup
        from app.services.password import hash_password

        password_hash = hash_password("admin123")
        user = User(
            username="admin",
            email="admin@example.com",
            role="admin",
            password_hash=password_hash,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def regular_user():
    """Create a regular user for testing"""
    db = TestingSessionLocal()
    try:
        user = User(
            username="regular",
            email="regular@example.com",
            role="user",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_admin_login_page():
    """Test accessing admin login page"""
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "Admin Login" in response.text
    assert "username" in response.text
    assert "password" in response.text


def test_admin_login_success(admin_user):
    """Test successful admin login"""
    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "admin123",
            "csrf_token": get_csrf_token(),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    # Check that session cookie is set
    assert "session" in response.cookies


def test_admin_login_invalid_username():
    """Test login with invalid username"""
    response = client.post(
        "/admin/login",
        data={
            "username": "nonexistent",
            "password": "admin123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_admin_login_invalid_password(admin_user):
    """Test login with invalid password"""
    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "wrongpassword",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_admin_login_non_admin_user(regular_user):
    """Test login with non-admin user"""
    # Add password to regular user
    from app.services.password import hash_password

    db = TestingSessionLocal()
    try:
        regular_user.password_hash = hash_password("user123")
        db.add(regular_user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/admin/login",
        data={
            "username": "regular",
            "password": "user123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 403
    assert "Admin access required" in response.text


def test_admin_login_inactive_user(admin_user):
    """Test login with inactive admin user"""
    db = TestingSessionLocal()
    try:
        admin_user.is_active = False
        db.add(admin_user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "admin123",
            "csrf_token": get_csrf_token(),
        },
    )
    assert response.status_code == 403
    assert "Account is inactive" in response.text


def test_admin_dashboard_requires_auth():
    """Test that admin dashboard requires authentication"""
    response = client.get("/admin")
    assert response.status_code == 401


def test_admin_dashboard_requires_admin_role(regular_user):
    """Test that admin dashboard requires admin role"""
    # Create session for regular user
    from app.services.session import session_manager

    session_token = session_manager.create_session(regular_user.id)
    response = client.get("/admin", cookies={"session": session_token})
    assert response.status_code == 403


def test_admin_dashboard_success(admin_user):
    """Test accessing admin dashboard with valid admin session"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    response = client.get("/admin", cookies={"session": session_token})
    assert response.status_code == 200
    assert "Admin Dashboard" in response.text
    assert "admin" in response.text


def test_admin_logout(admin_user):
    """Test admin logout"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    response = client.post(
        "/admin/logout",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"
    # Check that session cookie is deleted
    assert "session" not in response.cookies or response.cookies["session"] == ""


def test_create_user_form_requires_admin(admin_user):
    """Test that create user form requires admin"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    response = client.get("/admin/users/new", cookies={"session": session_token})
    assert response.status_code == 200
    assert "Create New User" in response.text


def _verify_user_created_with_api_key(
    username: str, expected_email: str, expected_role: str
) -> None:
    """Verify that a user was created with correct attributes, API key, and password."""
    from app.models import ApiKey

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None, f"User {username} should exist"
        assert user.email == expected_email
        assert user.role == expected_role
        assert user.is_active is True
        assert user.password_hash is not None, "Password hash should be set"

        api_key = (
            db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.is_active).first()
        )
        assert api_key is not None, "Active API key should exist for user"
    finally:
        db.close()


def _verify_user_can_login(username: str, password: str) -> None:
    """Verify that a user can successfully log in."""
    login_response = client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": get_csrf_token(),
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/account"
    assert "session" in login_response.cookies


def test_create_user_via_admin(admin_user):
    """Test creating a user via admin interface"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    response = client.post(
        "/admin/users/new",
        data={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "secure-password123",
            "role": "user",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": session_token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    # API key is now in flash message, not URL

    _verify_user_created_with_api_key("newuser", "newuser@example.com", "user")
    _verify_user_can_login("newuser", "secure-password123")


def test_create_user_duplicate(admin_user):
    """Test creating duplicate user via admin interface"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)

    # Create first user
    client.post(
        "/admin/users/new",
        data={
            "username": "duplicate",
            "email": "first@example.com",
            "password": "password123",
            "role": "user",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": session_token},
    )

    # Try to create duplicate
    response = client.post(
        "/admin/users/new",
        data={
            "username": "duplicate",
            "email": "second@example.com",
            "password": "password123",
            "role": "user",
            "csrf_token": get_csrf_token(),
        },
        cookies={"session": session_token},
    )
    assert response.status_code == 400
    assert "User already exists" in response.text


def test_toggle_user_status(admin_user, regular_user):
    """Test toggling user active status"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    user_id = regular_user.id

    # Initially active
    assert regular_user.is_active is True

    # Deactivate
    response = client.post(
        f"/admin/users/{user_id}/toggle",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_token},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Verify deactivated
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.is_active is False
    finally:
        db.close()

    # Reactivate
    response = client.post(
        f"/admin/users/{user_id}/toggle",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_token},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Verify reactivated
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.is_active is True
    finally:
        db.close()


def test_toggle_user_status_self(admin_user):
    """Test that admin cannot deactivate themselves"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)

    response = client.post(
        f"/admin/users/{admin_user.id}/toggle",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_token},
    )
    assert response.status_code == 400
    assert "Cannot deactivate your own account" in response.text


def test_regenerate_user_api_key(admin_user, regular_user):
    """Test regenerating user API key"""
    from app.models import ApiKey
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    user_id = regular_user.id

    # Get old API key
    db = TestingSessionLocal()
    try:
        old_api_key = (
            db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.is_active).first()
        )
        old_key_value = old_api_key.key if old_api_key else None
    finally:
        db.close()

    response = client.post(
        f"/admin/users/{user_id}/regenerate-key",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_token},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Verify API key changed
    db = TestingSessionLocal()
    try:
        new_api_key = (
            db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.is_active).first()
        )
        assert new_api_key is not None
        if old_key_value:
            assert new_api_key.key != old_key_value
    finally:
        db.close()


def test_regenerate_user_api_key_not_found(admin_user):
    """Test regenerating API key for non-existent user"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(admin_user.id)
    fake_id = uuid4()

    response = client.post(
        f"/admin/users/{fake_id}/regenerate-key",
        data={"csrf_token": get_csrf_token()},
        cookies={"session": session_token},
    )
    assert response.status_code == 404

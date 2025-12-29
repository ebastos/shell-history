"""Tests for users API endpoints"""

import secrets
from uuid import uuid4

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import ApiKey, User
from app.services.api_key import hash_api_key
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
def admin_api_key() -> str:
    """Create an admin user and return their API key"""
    db = TestingSessionLocal()
    try:
        admin = User(
            username="admin",
            email="admin@example.com",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        api_key_value = secrets.token_urlsafe(32)
        hashed_key = hash_api_key(api_key_value)
        api_key = ApiKey(
            user_id=admin.id,
            key=hashed_key,
            is_active=True,
        )
        db.add(api_key)
        db.commit()
        return api_key_value
    finally:
        db.close()


def test_list_users_requires_auth():
    """Test that listing users without auth returns 401"""
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_list_users_requires_admin(admin_api_key: str):
    """Test listing users with admin auth"""
    # Create a non-admin user to test with
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

        user_api_key = secrets.token_urlsafe(32)
        hashed_key = hash_api_key(user_api_key)
        api_key = ApiKey(user_id=user.id, key=hashed_key, is_active=True)
        db.add(api_key)
        db.commit()
    finally:
        db.close()

    # Non-admin should get 403
    response = client.get(
        "/api/v1/users",
        headers={"X-API-Key": user_api_key},
    )
    assert response.status_code == 403

    # Admin should succeed
    response = client.get(
        "/api/v1/users",
        headers={"X-API-Key": admin_api_key},
    )
    assert response.status_code == 200


def test_list_users_empty(admin_api_key: str):
    """Test listing users returns admin user"""
    response = client.get(
        "/api/v1/users",
        headers={"X-API-Key": admin_api_key},
    )
    assert response.status_code == 200
    data = response.json()
    # Admin user exists from fixture
    assert data["total"] == 1
    assert data["items"][0]["username"] == "admin"


def test_create_user(admin_api_key: str):
    """Test creating a new user (admin only)"""
    response = client.post(
        "/api/v1/users",
        headers={"X-API-Key": admin_api_key},
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "secret123",
            "role": "user",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "id" in data
    # Password should not be returned
    assert "password" not in data


def test_create_user_requires_auth():
    """Test that creating a user without auth returns 401"""
    response = client.post(
        "/api/v1/users",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "secret123",
            "role": "user",
        },
    )
    assert response.status_code == 401


def test_create_user_duplicate_username(admin_api_key: str):
    """Test that creating a user with duplicate username returns 400"""
    headers = {"X-API-Key": admin_api_key}
    client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "duplicate",
            "email": "first@example.com",
            "password": "pass",
        },
    )
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "duplicate",
            "email": "second@example.com",
            "password": "pass",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_user_duplicate_email(admin_api_key: str):
    """Test that creating a user with duplicate email returns 400"""
    headers = {"X-API-Key": admin_api_key}
    client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "user1",
            "email": "same@example.com",
            "password": "pass",
        },
    )
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "user2",
            "email": "same@example.com",
            "password": "pass",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_user(admin_api_key: str):
    """Test getting a user by ID (admin only)"""
    headers = {"X-API-Key": admin_api_key}
    create_response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "findme",
            "email": "findme@example.com",
            "password": "pass",
        },
    )
    user_id = create_response.json()["id"]
    response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "findme"


def test_get_user_not_found(admin_api_key: str):
    """Test getting a non-existent user returns 404"""
    fake_id = str(uuid4())
    response = client.get(
        f"/api/v1/users/{fake_id}",
        headers={"X-API-Key": admin_api_key},
    )
    assert response.status_code == 404

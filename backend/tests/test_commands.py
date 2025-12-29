"""Tests for command API endpoints"""

import pytest
from app.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.conftest import create_auth_headers

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
def test_user(db_session, test_user_factory):
    """Create a test user with API key"""
    return test_user_factory(db_session)


@pytest.fixture
def auth_headers(test_user, db_session):
    """Return headers with API key for authenticated requests"""
    return create_auth_headers(test_user, db_session)


def test_create_command(test_user, auth_headers):
    """Test creating a command via API"""
    response = client.post(
        "/api/v1/commands",
        json={"command": "ls -la", "hostname": "test-host", "username": "testuser"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "ls -la"
    assert data["hostname"] == "test-host"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "timestamp" in data


def test_create_command_requires_auth():
    """Test that creating a command without API key returns 401"""
    response = client.post(
        "/api/v1/commands",
        json={"command": "ls -la", "hostname": "test-host", "username": "testuser"},
    )
    assert response.status_code == 401


def test_filter_commands_by_hostname(test_user, auth_headers):
    """Test filtering commands by hostname (database query, no Meilisearch needed)"""
    # Create some commands
    client.post(
        "/api/v1/commands",
        json={
            "command": "docker-compose up",
            "hostname": "server01",
            "username": "alice",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/commands",
        json={
            "command": "docker-compose down",
            "hostname": "server01",
            "username": "alice",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/commands",
        json={"command": "npm install", "hostname": "laptop", "username": "bob"},
        headers=auth_headers,
    )

    # Filter by hostname
    response = client.get("/api/v1/commands?hostname=server01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2

    # Filter by username
    response = client.get("/api/v1/commands?username=bob", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["command"] == "npm install"


def test_get_command(test_user, auth_headers):
    """Test getting a single command"""
    # Create a command
    response = client.post(
        "/api/v1/commands",
        json={"command": "echo test", "hostname": "test-host", "username": "testuser"},
        headers=auth_headers,
    )
    cmd_id = response.json()["id"]

    # Get the command
    response = client.get(f"/api/v1/commands/{cmd_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cmd_id
    assert data["command"] == "echo test"


def test_delete_command(test_user, auth_headers):
    """Test deleting a command"""
    # Create a command
    response = client.post(
        "/api/v1/commands",
        json={"command": "to-delete", "hostname": "test-host", "username": "testuser"},
        headers=auth_headers,
    )
    cmd_id = response.json()["id"]

    # Delete the command
    response = client.delete(f"/api/v1/commands/{cmd_id}", headers=auth_headers)
    assert response.status_code == 200

    # Verify it's deleted
    response = client.get(f"/api/v1/commands/{cmd_id}", headers=auth_headers)
    assert response.status_code == 404


def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

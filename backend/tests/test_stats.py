"""Tests for stats API endpoint"""

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


def test_get_stats_empty_db(auth_headers):
    """Test getting stats with an empty database"""
    response = client.get("/api/v1/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_commands"] == 0
    assert data["active_hosts"] == 0
    assert "storage_used" in data


def test_get_stats_with_data(auth_headers):
    """Test getting stats after creating some data"""
    # Create some commands (which also creates hosts)
    client.post(
        "/api/v1/commands",
        json={"command": "ls", "hostname": "host1", "username": "user1"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/commands",
        json={"command": "pwd", "hostname": "host1", "username": "user1"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/commands",
        json={"command": "echo hello", "hostname": "host2", "username": "user2"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_commands"] == 3
    assert data["active_hosts"] == 2


def test_get_stats_requires_auth():
    """Test that stats endpoint requires authentication"""
    response = client.get("/api/v1/stats")
    assert response.status_code == 401


def test_stats_counts_only_user_data(db_session, test_user_factory):
    """Test that stats only count the current user's data (multi-tenancy)"""
    # Create first user and add commands
    user1 = test_user_factory(db_session, username="user1", email="user1@example.com")
    headers1 = create_auth_headers(user1, db_session)
    client.post(
        "/api/v1/commands",
        json={"command": "ls", "hostname": "host1", "username": "user1"},
        headers=headers1,
    )
    client.post(
        "/api/v1/commands",
        json={"command": "pwd", "hostname": "host1", "username": "user1"},
        headers=headers1,
    )

    # Create second user and add commands
    user2 = test_user_factory(db_session, username="user2", email="user2@example.com")
    headers2 = create_auth_headers(user2, db_session)
    client.post(
        "/api/v1/commands",
        json={"command": "echo test", "hostname": "host2", "username": "user2"},
        headers=headers2,
    )

    # User1 should only see their 2 commands
    response1 = client.get("/api/v1/stats", headers=headers1)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["total_commands"] == 2
    assert data1["active_hosts"] == 1

    # User2 should only see their 1 command
    response2 = client.get("/api/v1/stats", headers=headers2)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total_commands"] == 1
    assert data2["active_hosts"] == 1

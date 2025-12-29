"""Tests for hosts API endpoints"""

from uuid import uuid4

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
def test_user(db_session, test_user_factory):
    """Create a test user with API key"""
    return test_user_factory(db_session)


@pytest.fixture
def auth_headers(test_user, db_session):
    """Return headers with API key for authenticated requests"""
    return create_auth_headers(test_user, db_session)


def test_list_hosts_empty(auth_headers):
    """Test listing hosts when none exist"""
    response = client.get("/api/v1/hosts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_create_host(auth_headers):
    """Test creating a new host"""
    response = client.post(
        "/api/v1/hosts",
        json={"hostname": "server01", "ip_address": "192.168.1.1", "os_type": "linux"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "server01"
    assert data["ip_address"] == "192.168.1.1"
    assert data["os_type"] == "linux"
    assert data["is_active"] is True
    assert "id" in data


def test_create_host_duplicate(auth_headers):
    """Test that creating a duplicate host returns 400"""
    client.post(
        "/api/v1/hosts",
        json={"hostname": "server01"},
        headers=auth_headers,
    )
    response = client.post(
        "/api/v1/hosts",
        json={"hostname": "server01"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_get_host(auth_headers):
    """Test getting a host by ID"""
    create_response = client.post(
        "/api/v1/hosts",
        json={"hostname": "myhost"},
        headers=auth_headers,
    )
    host_id = create_response.json()["id"]
    response = client.get(f"/api/v1/hosts/{host_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["hostname"] == "myhost"


def test_get_host_not_found(auth_headers):
    """Test getting a non-existent host returns 404"""
    fake_id = str(uuid4())
    response = client.get(f"/api/v1/hosts/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


def test_deactivate_host(auth_headers):
    """Test deactivating a host"""
    create_response = client.post(
        "/api/v1/hosts",
        json={"hostname": "to-deactivate"},
        headers=auth_headers,
    )
    host_id = create_response.json()["id"]
    response = client.put(f"/api/v1/hosts/{host_id}/deactivate", headers=auth_headers)
    assert response.status_code == 200
    get_response = client.get(f"/api/v1/hosts/{host_id}", headers=auth_headers)
    assert get_response.json()["is_active"] is False


def test_list_hosts_active_only(auth_headers):
    """Test filtering for active hosts only"""
    # Create two hosts
    client.post("/api/v1/hosts", json={"hostname": "active-host"}, headers=auth_headers)
    resp2 = client.post(
        "/api/v1/hosts", json={"hostname": "inactive-host"}, headers=auth_headers
    )

    # Deactivate one
    client.put(f"/api/v1/hosts/{resp2.json()['id']}/deactivate", headers=auth_headers)

    # List all hosts
    all_response = client.get("/api/v1/hosts", headers=auth_headers)
    assert all_response.json()["total"] == 2

    # List only active hosts
    active_response = client.get("/api/v1/hosts?active_only=true", headers=auth_headers)
    assert active_response.json()["total"] == 1
    assert active_response.json()["items"][0]["hostname"] == "active-host"

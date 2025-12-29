from unittest.mock import patch

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


# Mock data simulating what Meilisearch returns
MOCK_SEARCH_RESULTS = {
    "hits": [
        {
            "id": "c308bb8b-9e1e-436f-87ca-1c251f2f3d2f",  # Use a valid UUID string
            "command": "ls -la",
            "hostname": "test-host",
            "username": "testuser",
            "timestamp": "2024-01-01T12:00:00Z",
        }
    ],
    "total": 1,
}


def test_search_commands_mocked(auth_headers):
    """Test searching commands with a mocked search service to verify fixed logic"""
    with patch(
        "app.routers.commands.search_service.search", return_value=MOCK_SEARCH_RESULTS
    ):
        response = client.get("/api/v1/commands?q=ls", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify formatting
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["command"] == "ls -la"

        # Verify the timestamp was converted from string to a format JSON likes
        # (FastAPI will re-serialize it as ISO string, but we want to know
        # the code didn't crash and handled the datetime conversion internally)
        assert "2024-01-01T12:00:00" in data["items"][0]["timestamp"]


def test_ui_search_mocked(auth_headers):
    """Test the UI search endpoint with a mocked search service"""
    with patch(
        "app.routers.commands.search_service.search", return_value=MOCK_SEARCH_RESULTS
    ):
        response = client.get("/ui/search?q=ls", headers=auth_headers)

        assert response.status_code == 200
        # Should return HTML
        assert "ls -la" in response.text
        assert "test-host" in response.text
        assert "1 commands found" in response.text

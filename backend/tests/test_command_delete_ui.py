"""Tests for command deletion from UI"""

import pytest
from app.database import Base, get_db
from app.main import app
from app.models import Command, Host, User
from app.services.password import hash_password
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
    """Create an authenticated session"""
    from app.services.session import session_manager

    session_token = session_manager.create_session(test_user_with_password.id)
    return session_token


@pytest.fixture
def test_command(test_user_with_password, db_session):
    """Create a test command"""
    host = Host(hostname="testhost", user_id=test_user_with_password.id)
    db_session.add(host)
    db_session.commit()
    db_session.refresh(host)

    command = Command(
        command="ls -la",
        hostname="testhost",
        username="testuser",
        user_id=test_user_with_password.id,
        host_id=host.id,
    )
    db_session.add(command)
    db_session.commit()
    db_session.refresh(command)
    return command


def test_delete_command_requires_auth(test_command):
    """Test that delete command requires authentication"""
    response = client.delete(f"/ui/commands/{test_command.id}")
    assert response.status_code == 401


def test_delete_command_success(test_command, authenticated_session):
    """Test successful command deletion"""
    command_id = test_command.id

    response = client.delete(
        f"/ui/commands/{command_id}",
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 200

    # Verify command was deleted
    db = TestingSessionLocal()
    try:
        deleted_command = db.query(Command).filter(Command.id == command_id).first()
        assert deleted_command is None
    finally:
        db.close()


def test_delete_command_not_found(authenticated_session):
    """Test deleting a non-existent command"""
    from uuid import uuid4

    fake_id = uuid4()
    response = client.delete(
        f"/ui/commands/{fake_id}",
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 404


def test_delete_other_user_command(
    test_user_with_password, authenticated_session, db_session
):
    """Test that users cannot delete other users' commands"""
    # Create another user
    password_hash = hash_password("otherpass")
    other_user = User(
        username="otheruser",
        email="other@example.com",
        role="user",
        password_hash=password_hash,
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    # Create command for other user
    host = Host(hostname="otherhost", user_id=other_user.id)
    db_session.add(host)
    db_session.commit()
    db_session.refresh(host)

    other_command = Command(
        command="echo test",
        hostname="otherhost",
        username="otheruser",
        user_id=other_user.id,
        host_id=host.id,
    )
    db_session.add(other_command)
    db_session.commit()
    db_session.refresh(other_command)

    # Try to delete other user's command
    response = client.delete(
        f"/ui/commands/{other_command.id}",
        cookies={"session": authenticated_session},
    )
    assert response.status_code == 404  # Should not find it (user isolation)

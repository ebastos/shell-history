"""SQLAlchemy data models"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship


class Command(Base):  # type: ignore[misc]
    """Represents a captured shell command"""

    __tablename__ = "commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    command = Column(Text, nullable=False)
    hostname = Column(String, nullable=False, index=True)
    username = Column(String, nullable=False, index=True)
    alt_username = Column(String, nullable=True)
    cwd = Column(String, nullable=True)
    old_pwd = Column(String, nullable=True)
    exit_code = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    session_id = Column(String, nullable=True)
    redacted = Column(Boolean, default=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=True)

    user = relationship("User", back_populates="commands")
    host = relationship("Host", back_populates="commands")


class Host(Base):  # type: ignore[misc]
    """Represents a machine from which commands are captured"""

    __tablename__ = "hosts"
    __table_args__ = (UniqueConstraint("hostname", "user_id", name="uq_hostname_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    os_type = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    user = relationship("User", back_populates="hosts")
    commands = relationship("Command", back_populates="host")


class User(Base):  # type: ignore[misc]
    """System user account for access control"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="user")  # admin, user, readonly
    password_hash = Column(String, nullable=True)  # Only for admin users
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    commands = relationship("Command", back_populates="user")
    hosts = relationship("Host", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")


class ApiKey(Base):  # type: ignore[misc]
    """API key for user authentication"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    key = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)  # User-friendly label
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="api_keys")


class PasswordResetToken(Base):  # type: ignore[misc]
    """Token for password reset requests"""

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="password_reset_tokens")


class EmailVerificationToken(Base):  # type: ignore[misc]
    """Token for email verification (email change)"""

    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    new_email = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="email_verification_tokens")

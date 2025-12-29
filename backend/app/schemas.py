"""Pydantic schemas for request/response validation"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Command schemas
class CommandCreate(BaseModel):
    """Schema for creating a command"""

    command: str
    hostname: str
    username: str
    alt_username: str | None = None
    cwd: str | None = None
    old_pwd: str | None = None
    exit_code: int | None = None
    session_id: str | None = None
    redacted: bool = False  # Client indicates if redaction was applied


class CommandResponse(CommandCreate):
    """Schema for command response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    redacted: bool


# Host schemas
class HostCreate(BaseModel):
    """Schema for creating a host"""

    hostname: str
    ip_address: str | None = None
    os_type: str | None = None


class HostResponse(HostCreate):
    """Schema for host response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    last_seen: datetime


# User schemas
class UserCreate(BaseModel):
    """Schema for creating a user"""

    username: str
    email: str
    password: str
    role: str | None = "user"


class UserResponse(BaseModel):
    """Schema for user response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserMeResponse(BaseModel):
    """Schema for current user response (includes first active API key)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    role: str
    api_key: str | None  # First active API key, if any
    created_at: datetime

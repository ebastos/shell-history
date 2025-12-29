"""User management endpoints"""

import secrets
from uuid import UUID

from app.database import get_db
from app.models import ApiKey, User
from app.schemas import UserCreate, UserMeResponse, UserResponse
from app.services.api_key import hash_api_key
from app.services.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/")
async def list_users(  # type: ignore[no-untyped-def]
    page: int = 0,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):  # Return type omitted: FastAPI/Pydantic can't serialize SQLAlchemy objects in dict
    """List all users (admin only)"""
    query = db.query(User)
    total = query.count()
    users = query.offset(page * page_size).limit(page_size).all()

    return {
        "items": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page + 1) * page_size < total,
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Get a user by ID (admin only)"""
    user: User | None = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Create a new user"""
    # Check if user already exists
    existing = (
        db.query(User)
        .filter((User.username == user.username) | (User.email == user.email))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Generate API key for new user
    api_key_value = secrets.token_urlsafe(32)
    api_key_hash = hash_api_key(api_key_value)

    db_user = User(
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create API key (store hashed, return plaintext only in response)
    api_key = ApiKey(
        user_id=db_user.id,
        key=api_key_hash,  # Store hashed key
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserMeResponse:
    """Get current authenticated user information"""
    # API keys are hashed and cannot be returned - set to None
    # Keys are only shown once when created
    setattr(current_user, "api_key", None)
    return current_user


@router.post("/me/api-key/regenerate", response_model=UserMeResponse)
async def regenerate_api_key(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserMeResponse:
    """Regenerate API key for current user"""
    # Deactivate all existing API keys for this user
    db.query(ApiKey).filter(ApiKey.user_id == current_user.id, ApiKey.is_active).update(
        {"is_active": False}
    )

    # Create new API key
    new_api_key_value = secrets.token_urlsafe(32)
    new_api_key_hash = hash_api_key(new_api_key_value)
    new_api_key = ApiKey(
        user_id=current_user.id,
        key=new_api_key_hash,  # Store hashed key
        is_active=True,
    )
    db.add(new_api_key)
    db.commit()
    db.refresh(current_user)
    # Return plaintext key only in response (shown once)
    setattr(current_user, "api_key", new_api_key_value)
    return current_user

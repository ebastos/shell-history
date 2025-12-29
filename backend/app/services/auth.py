"""Authentication service for API key and session validation"""

from datetime import datetime

from app.database import get_db
from app.models import ApiKey, User
from app.services.api_key import verify_api_key
from app.services.session import session_manager
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session


async def get_current_user(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user from API key or session.

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: 401 if authentication is missing or invalid
    """
    # Try API key first (for API clients)
    if x_api_key:
        # Find API key by checking all active keys (since keys are now hashed)
        # This is less efficient but necessary for security
        active_keys = db.query(ApiKey).filter(ApiKey.is_active).all()
        api_key_obj: ApiKey | None = None

        for key_obj in active_keys:
            # Verify against hashed key
            if verify_api_key(x_api_key, key_obj.key):
                api_key_obj = key_obj
                break

        if not api_key_obj:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
            )

        user: User = api_key_obj.user
        if not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="User account is inactive",
            )

        # Update last_used_at timestamp
        api_key_obj.last_used_at = datetime.utcnow()
        db.commit()

        return user

    # Try session cookie (for web UI)
    session_token = request.cookies.get("session")
    if session_token:
        user_id = session_manager.verify_session(session_token)
        if user_id:
            session_user: User | None = (
                db.query(User).filter(User.id == user_id).first()
            )
            if session_user and session_user.is_active:
                return session_user
            if session_user:
                raise HTTPException(
                    status_code=401,
                    detail="User account is inactive",
                )

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide X-API-Key header or valid session.",
    )


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to require admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        User object if admin

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user

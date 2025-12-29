"""CSRF protection for FastAPI"""

from app.services.csrf import csrf_service
from fastapi import Form, Header, HTTPException, Request


async def verify_csrf_token(
    request: Request,
    csrf_token: str | None = Form(None),
    x_csrf_token: str | None = Header(None, alias="X-CSRF-Token"),
) -> None:
    """Dependency to verify CSRF token from form or header.

    Use this as a dependency in POST endpoints that need CSRF protection.

    Args:
        request: FastAPI request object
        csrf_token: CSRF token from form data
        x_csrf_token: CSRF token from header (for HTMX requests)

    Raises:
        HTTPException: 403 if CSRF token is invalid
    """
    # Skip for API endpoints (they use API keys)
    if request.url.path.startswith("/api/"):
        return

    # Check header first, then form
    token = x_csrf_token or csrf_token

    if not token or not csrf_service.verify_token(token):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token")

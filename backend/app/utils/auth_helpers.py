"""Authentication helper utilities"""

from typing import Union

from app.config import settings
from app.models import User
from app.services.password import verify_password
from app.services.rate_limit import get_client_ip, rate_limiter
from app.services.session import session_manager
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session


def handle_login(
    request: Request,
    username: str,
    password: str,
    db: Session,
    templates: Jinja2Templates,
    template_name: str,
    redirect_url: str,
    rate_limit_key: str,
    require_admin: bool = False,
) -> Union[RedirectResponse, HTMLResponse]:
    """Handle login logic shared between admin and user login.

    Args:
        request: FastAPI request object
        username: Username from form
        password: Password from form
        db: Database session
        templates: Jinja2 templates instance
        template_name: Template to use for error responses
        redirect_url: URL to redirect to on success
        rate_limit_key: Key for rate limiting
        require_admin: Whether to require admin role

    Returns:
        RedirectResponse on success, TemplateResponse on error
    """
    # Rate limiting: 5 attempts per 15 minutes per IP
    client_ip = get_client_ip(request)
    allowed, remaining = rate_limiter.is_allowed(
        f"{rate_limit_key}:{client_ip}", max_requests=5, window_seconds=900
    )
    if not allowed:
        return templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "error": "Too many login attempts. Please try again in 15 minutes.",
            },
            status_code=429,
        )

    # Find user by username
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return templates.TemplateResponse(
            template_name,
            {"request": request, "error": "Invalid username or password"},
            status_code=401,
        )

    # Verify password
    if not user.password_hash or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            template_name,
            {"request": request, "error": "Invalid username or password"},
            status_code=401,
        )

    # Check if admin required
    if require_admin and user.role != "admin":
        return templates.TemplateResponse(
            template_name,
            {"request": request, "error": "Admin access required"},
            status_code=403,
        )

    # Check if active
    if not user.is_active:
        return templates.TemplateResponse(
            template_name,
            {"request": request, "error": "Account is inactive"},
            status_code=403,
        )

    # Create session
    session_token = session_manager.create_session(user.id)

    # Set cookie and redirect
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=session_manager.expire_hours * 3600,
    )
    return response


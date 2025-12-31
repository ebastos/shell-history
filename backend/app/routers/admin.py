"""Admin interface router for tenant management"""

import secrets
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.middleware.csrf import verify_csrf_token
from app.models import ApiKey, User
from app.services.api_key import hash_api_key
from app.services.auth import require_admin
from app.services.flash import flash_service
from app.services.password import hash_password
from app.ui_utils import templates
from app.utils.auth_helpers import handle_login
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(tags=["admin"])


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request) -> HTMLResponse:
    """Display admin login page."""
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Handle admin login and create session."""
    return handle_login(
        request=request,
        username=username,
        password=password,
        db=db,
        templates=templates,
        template_name="admin/login.html",
        redirect_url="/admin",
        rate_limit_key="admin_login",
        require_admin=True,
    )


@router.post("/admin/logout")
async def admin_logout(
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Handle admin logout and clear session."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="session")
    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    page: int = 0,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    """Display admin dashboard with user list."""
    query = db.query(User).order_by(User.created_at.desc())
    total = query.count()
    users = query.offset(page * page_size).limit(page_size).all()

    # Load API keys for each user (first active key for display)
    # Note: Keys are hashed, so we can't display them - just show that a key exists
    for user in users:
        first_key: ApiKey | None = (
            db.query(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.is_active).first()
        )
        # Keys are hashed, so we can't show the actual key
        setattr(user, "api_key", None if not first_key else "[HIDDEN]")

    # Get flash message if present
    flash_cookie = request.cookies.get("flash")
    flash_message = None
    flash_category = None
    if flash_cookie:
        flash_result = flash_service.get_flash(flash_cookie)
        if flash_result:
            flash_message, flash_category = flash_result

    response = templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page + 1) * page_size < total,
            "flash_message": flash_message,
            "flash_category": flash_category,
            "user": current_user,
        },
    )

    # Clear flash cookie after reading
    if flash_cookie:
        response.delete_cookie(key="flash")

    return response


@router.get("/admin/users/new", response_class=HTMLResponse)
async def new_user_form(
    request: Request,
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    """Display form to create a new user."""
    return templates.TemplateResponse("admin/user_form.html", {"request": request})


@router.post("/admin/users/new", response_class=HTMLResponse)
async def create_user_admin(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Create a new user from admin interface."""
    # Check if user already exists
    existing = (
        db.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )
    if existing:
        return templates.TemplateResponse(
            "admin/user_form.html",
            {"request": request, "error": "User already exists"},
            status_code=400,
        )

    # Validate role
    if role not in ["user", "admin", "readonly"]:
        role = "user"

    # Hash password
    password_hash = hash_password(password)

    # Generate API key for new user
    api_key_value = secrets.token_urlsafe(32)
    api_key_hash = hash_api_key(api_key_value)

    db_user = User(
        username=username,
        email=email,
        role=role,
        password_hash=password_hash,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create API key (store hashed)
    api_key = ApiKey(
        user_id=db_user.id,
        key=api_key_hash,  # Store hashed key
        is_active=True,
    )
    db.add(api_key)
    db.commit()

    # Set flash message with API key (shown once)
    flash_cookie = flash_service.set_flash(
        f"User '{username}' created successfully. API Key: {api_key_value}", "success"
    )

    # Redirect to dashboard
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="flash",
        value=flash_cookie,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=300,  # 5 minutes
    )
    return response


@router.post("/admin/users/{user_id}/toggle")
async def toggle_user_status(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Toggle user active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deactivating yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Cannot deactivate your own account"
        )

    user.is_active = not user.is_active
    db.commit()

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/{user_id}/regenerate-key")
async def regenerate_user_api_key(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Regenerate API key for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Deactivate all existing API keys for this user
    db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.is_active).update(
        {"is_active": False}
    )

    # Create new API key
    new_api_key_value = secrets.token_urlsafe(32)
    new_api_key_hash = hash_api_key(new_api_key_value)
    new_api_key = ApiKey(
        user_id=user.id,
        key=new_api_key_hash,  # Store hashed key
        is_active=True,
    )
    db.add(new_api_key)
    db.commit()

    # Set flash message with API key (shown once)
    flash_cookie = flash_service.set_flash(
        f"API key regenerated for '{user.username}'. New API Key: {new_api_key_value}",
        "success",
    )

    # Redirect to dashboard
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="flash",
        value=flash_cookie,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=300,  # 5 minutes
    )
    return response

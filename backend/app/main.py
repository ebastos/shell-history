"""Shell History Collector Service - Main Application"""

import os
import secrets

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models import ApiKey, User
from app.routers import admin, commands, hosts, stats, ui, user_ui, users
from app.services.api_key import hash_api_key
from app.services.auth import get_current_user
from app.services.csrf import csrf_service
from app.services.password import hash_password
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Create database tables
Base.metadata.create_all(bind=engine)


def bootstrap_admin() -> None:
    """Create initial admin user from environment variables if not exists."""
    if not all(
        [settings.admin_username, settings.admin_email, settings.admin_password]
    ):
        return  # Skip if env vars not set

    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = (
            db.query(User)
            .filter(
                (User.username == settings.admin_username)
                | (User.email == settings.admin_email)
            )
            .first()
        )
        if existing_admin:
            return  # Admin already exists

        # Create admin user
        password_hash = hash_password(settings.admin_password)
        api_key_value = secrets.token_urlsafe(32)
        api_key_hash = hash_api_key(api_key_value)

        admin_user = User(
            username=settings.admin_username,
            email=settings.admin_email,
            role="admin",
            password_hash=password_hash,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Create API key for admin user (store hashed)
        api_key = ApiKey(
            user_id=admin_user.id,
            key=api_key_hash,  # Store hashed key
            is_active=True,
        )
        db.add(api_key)
        db.commit()
    finally:
        db.close()


# Get current file directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="Shell History Collector",
    description="Centralized shell command history collection and search",
    version="0.1.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> RedirectResponse | JSONResponse:
    """Handle HTTP exceptions - redirect HTML requests to appropriate login pages."""
    # Only handle 401 (Unauthorized) errors for browser requests
    if exc.status_code == 401:
        # Check if this is a browser request (not API or test client)
        # Browsers typically send Accept: text/html
        accept_header = request.headers.get("accept", "").lower()
        is_browser_request = (
            "text/html" in accept_header and "application/json" not in accept_header
        )

        # Also check if it's a UI route (not API route)
        is_ui_route = (
            request.url.path.startswith("/admin")
            or request.url.path.startswith("/account")
            or request.url.path.startswith("/history")
        ) and not request.url.path.startswith("/api/")

        # Only redirect browser requests to UI routes
        if is_browser_request and is_ui_route:
            # Redirect to appropriate login page
            if request.url.path.startswith("/admin"):
                return RedirectResponse(url="/admin/login", status_code=303)
            else:
                return RedirectResponse(url="/login", status_code=303)

    # For other cases, return JSON response (default FastAPI behavior)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.on_event("startup")
async def startup_event() -> None:
    """Bootstrap admin user on application startup."""
    # Validate critical security settings
    if not settings.secret_key or settings.secret_key == "change-me-in-production":
        if settings.environment == "production":
            raise ValueError(
                "SECRET_KEY must be set in production. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    bootstrap_admin()


# Security headers middleware - add security headers to all responses
app.add_middleware(SecurityHeadersMiddleware)

# Note: CSRF protection is implemented via dependency injection (verify_csrf_token)
# in individual form endpoints, not as middleware

# CORS middleware - only add if origins are configured
# Never allow "*" with credentials=True for security
if settings.cors_origins:
    origins = [
        origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-CSRF-Token"],
    )

# Mount static files
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)

# Templates with CSRF token context
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# Add CSRF token helper to template globals
# This makes csrf_token() available in all templates
def get_csrf_token() -> str:
    """Generate a CSRF token for templates"""
    return csrf_service.generate_token()


# Register as a global function that can be called in templates
templates.env.globals["csrf_token"] = get_csrf_token

# Include routers
app.include_router(commands.router, prefix="/api/v1")
app.include_router(hosts.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(ui.router)
app.include_router(user_ui.router)
app.include_router(admin.router)


@app.get("/history")
async def history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Command history page"""
    # Fetch initial commands
    results = await commands.search_commands(
        db=db, page=0, page_size=50, current_user=current_user
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "commands": results["items"],
            "total": results["total"],
            "user": current_user,
        },
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}

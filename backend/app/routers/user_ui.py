"""User-facing UI router for login, account, and API key management"""

import secrets
from datetime import datetime, timedelta
from uuid import UUID

from app.database import get_db
from app.middleware.csrf import verify_csrf_token
from app.models import ApiKey, EmailVerificationToken, PasswordResetToken, User
from app.services.api_key import hash_api_key
from app.services.auth import get_current_user
from app.services.email import send_email
from app.services.password import hash_password, verify_password
from app.services.rate_limit import get_client_ip, rate_limiter
from app.ui_utils import templates
from app.utils.auth_helpers import handle_login
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(tags=["user_ui"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Display user login page."""
    return templates.TemplateResponse("user/login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Handle user login and create session."""
    return handle_login(
        request=request,
        username=username,
        password=password,
        db=db,
        templates=templates,
        template_name="user/login.html",
        redirect_url="/account",
        rate_limit_key="login",
        require_admin=False,
    )


@router.post("/logout")
async def logout(
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Handle user logout and clear session."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response


@router.get("/account", response_class=HTMLResponse)
async def account_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    email_verified: str | None = Query(None),
) -> HTMLResponse:
    """Display user account dashboard with API keys."""
    # Load user's API keys
    api_keys = [
        key for key in current_user.api_keys if key.is_active
    ]  # Only show active keys

    return templates.TemplateResponse(
        "user/account.html",
        {
            "request": request,
            "user": current_user,
            "api_keys": api_keys,
            "email_verified": email_verified == "true",
        },
    )


@router.post("/account/api-keys", response_class=HTMLResponse)
async def create_api_key(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> HTMLResponse:
    """Create a new API key for the current user."""
    # Generate new API key
    new_key_plaintext = secrets.token_urlsafe(32)
    new_key_hash = hash_api_key(new_key_plaintext)

    api_key = ApiKey(
        user_id=current_user.id,
        key=new_key_hash,  # Store hashed key
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Temporarily set plaintext key for display (shown once)
    setattr(api_key, "key", new_key_plaintext)

    # Return HTML partial with the new key (shown once)
    return templates.TemplateResponse(
        "user/partials/api_key_item.html",
        {
            "request": request,
            "api_key": api_key,
            "show_key": True,  # Show the full key on creation
        },
    )


@router.post("/account/api-keys/{api_key_id}/revoke", response_class=HTMLResponse)
async def revoke_api_key(
    api_key_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> HTMLResponse:
    """Revoke (deactivate) an API key."""
    # Find the API key
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.id == api_key_id, ApiKey.user_id == current_user.id)
        .first()
    )

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Deactivate the key
    api_key.is_active = False
    db.commit()

    # Return empty response (HTMX will remove the element)
    return HTMLResponse(content="", status_code=200)


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request) -> HTMLResponse:
    """Display forgot password page."""
    return templates.TemplateResponse("user/forgot_password.html", {"request": request})


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> HTMLResponse:
    """Handle forgot password request."""
    # Rate limiting: 3 requests per hour per IP
    client_ip = get_client_ip(request)
    allowed, remaining = rate_limiter.is_allowed(
        f"forgot_password:{client_ip}", max_requests=3, window_seconds=3600
    )
    if not allowed:
        return templates.TemplateResponse(
            "user/forgot_password.html",
            {
                "request": request,
                "error": "Too many password reset requests. Please try again later.",
            },
            status_code=429,
        )

    # Find user by email
    user = db.query(User).filter(User.email == email, User.is_active).first()

    # Always return success (security: don't reveal if email exists)
    # But only send email if user exists and is active
    if user:
        # Generate secure token
        token_value = secrets.token_urlsafe(32)

        # Create reset token (24 hour expiry)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_value,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(reset_token)
        db.commit()

        # Build reset URL
        reset_url = f"{request.base_url}reset-password?token={token_value}"

        # Send email
        try:
            # Render email template using Jinja2 environment
            template = templates.env.get_template("emails/password_reset.html")
            email_html = template.render(reset_url=reset_url, username=user.username)
            send_email(
                to_email=user.email,
                subject="Password Reset Request",
                html_body=email_html,
            )
        except Exception:
            # Log error but don't reveal to user
            pass

    # Always show success message
    return templates.TemplateResponse(
        "user/forgot_password.html",
        {
            "request": request,
            "success": True,
            "message": "If that email address exists, a password reset link has been sent.",
        },
    )


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Display reset password page."""
    # Validate token
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not reset_token:
        return templates.TemplateResponse(
            "user/reset_password.html",
            {
                "request": request,
                "error": "Invalid or expired reset token. Please request a new password reset.",
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        "user/reset_password.html", {"request": request, "token": token}
    )


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> Response:
    """Handle password reset."""
    # Validate password length
    if len(password) < 8:
        return templates.TemplateResponse(
            "user/reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Password must be at least 8 characters long.",
            },
            status_code=400,
        )

    # Find and validate token
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not reset_token:
        return templates.TemplateResponse(
            "user/reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Invalid or expired reset token. Please request a new password reset.",
            },
            status_code=400,
        )

    # Update user password
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        return templates.TemplateResponse(
            "user/reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "User not found.",
            },
            status_code=400,
        )

    user.password_hash = hash_password(password)
    reset_token.used_at = datetime.utcnow()
    db.commit()

    # Redirect to login
    return RedirectResponse(url="/login?reset=success", status_code=303)


@router.post("/account/change-email", response_class=HTMLResponse)
async def change_email(
    request: Request,
    new_email: str = Form(...),
    password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> HTMLResponse:
    """Handle email change request."""
    # Verify current password
    if not current_user.password_hash or not verify_password(
        password, current_user.password_hash
    ):
        return templates.TemplateResponse(
            "user/partials/change_email_form.html",
            {
                "request": request,
                "error": "Invalid password. Please try again.",
            },
            status_code=400,
        )

    # Check if new email is different
    if new_email.lower() == current_user.email.lower():
        return templates.TemplateResponse(
            "user/partials/change_email_form.html",
            {
                "request": request,
                "error": "New email must be different from your current email.",
            },
            status_code=400,
        )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == new_email).first()
    if existing_user:
        return templates.TemplateResponse(
            "user/partials/change_email_form.html",
            {
                "request": request,
                "error": "This email address is already in use.",
            },
            status_code=400,
        )

    # Generate secure token
    token_value = secrets.token_urlsafe(32)

    # Create verification token (24 hour expiry)
    verification_token = EmailVerificationToken(
        user_id=current_user.id,
        new_email=new_email,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(verification_token)
    db.commit()

    # Build verification URL
    verify_url = f"{request.base_url}verify-email?token={token_value}"

    # Send verification email
    try:
        # Render email template using Jinja2 environment
        template = templates.env.get_template("emails/email_verification.html")
        email_html = template.render(
            verify_url=verify_url, username=current_user.username, new_email=new_email
        )
        send_email(
            to_email=new_email,
            subject="Verify Your New Email Address",
            html_body=email_html,
        )
    except Exception:
        # Log error but still show success to user
        pass

    # Return success message
    return templates.TemplateResponse(
        "user/partials/change_email_form.html",
        {
            "request": request,
            "success": True,
            "message": f"Verification email sent to {new_email}. Please check your inbox.",
        },
    )


@router.post("/account/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_token),
) -> HTMLResponse:
    """Handle password change request."""
    # Verify current password
    if not current_user.password_hash or not verify_password(
        current_password, current_user.password_hash
    ):
        return templates.TemplateResponse(
            "user/partials/change_password_form.html",
            {
                "request": request,
                "error": "Invalid current password. Please try again.",
            },
            status_code=400,
        )

    # Verify new passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "user/partials/change_password_form.html",
            {
                "request": request,
                "error": "New passwords do not match.",
            },
            status_code=400,
        )

    # Verify password length
    if len(new_password) < 8:
        return templates.TemplateResponse(
            "user/partials/change_password_form.html",
            {
                "request": request,
                "error": "New password must be at least 8 characters long.",
            },
            status_code=400,
        )

    # Update password
    current_user.password_hash = hash_password(new_password)
    db.commit()

    return templates.TemplateResponse(
        "user/partials/change_password_form.html",
        {
            "request": request,
            "success": True,
            "message": "Password updated successfully.",
        },
    )


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(
    request: Request,
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """Handle email verification."""
    # Find and validate token
    verification_token = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.token == token,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not verification_token:
        return templates.TemplateResponse(
            "user/account.html",
            {
                "request": request,
                "user": None,
                "api_keys": [],
                "error": "Invalid or expired verification token.",
            },
            status_code=400,
        )

    # Update user email
    user = db.query(User).filter(User.id == verification_token.user_id).first()
    if not user:
        return templates.TemplateResponse(
            "user/account.html",
            {
                "request": request,
                "user": None,
                "api_keys": [],
                "error": "User not found.",
            },
            status_code=400,
        )

    user.email = verification_token.new_email
    verification_token.used_at = datetime.utcnow()
    db.commit()

    # Redirect to account page with success message
    return RedirectResponse(url="/account?email_verified=true", status_code=303)

"""UI router for HTMX-based web interface"""

import os
from uuid import UUID

from app.database import get_db
from app.models import Command, User
from app.routers.commands import search_commands
from app.services.auth import get_current_user
from app.services.csrf import csrf_service
from app.services.search import search_service
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

router = APIRouter(tags=["ui"])

# Templates path relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# Add CSRF token function to templates
def get_csrf_token() -> str:
    """Generate a CSRF token for templates"""
    return csrf_service.generate_token()


templates.env.globals["csrf_token"] = get_csrf_token


@router.get("/ui/search")
async def ui_search(
    request: Request,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """HTMX search endpoint that returns HTML partial"""
    results = await search_commands(
        q=q, db=db, page=0, page_size=50, current_user=current_user
    )
    return templates.TemplateResponse(
        "partials/command_list.html",
        {"request": request, "commands": results["items"], "total": results["total"]},
    )


@router.delete("/ui/commands/{command_id}", response_class=HTMLResponse)
async def delete_command_ui(
    command_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Delete a command from UI (returns empty response for HTMX to remove element)"""
    command = (
        db.query(Command)
        .filter(Command.id == command_id, Command.user_id == current_user.id)
        .first()
    )
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    # Remove from search index
    search_service.delete_command(str(command_id))

    db.delete(command)
    db.commit()

    # Return empty response (HTMX will remove the element with hx-swap="outerHTML")
    return HTMLResponse(content="", status_code=200)

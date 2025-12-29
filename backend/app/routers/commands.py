"""Command ingestion and search endpoints"""

from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models import Command, Host, User
from app.schemas import CommandCreate, CommandResponse
from app.services.auth import get_current_user
from app.services.rate_limit import rate_limiter
from app.services.search import search_service
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("/", response_model=CommandResponse)
async def create_command(
    cmd: CommandCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommandResponse:
    """Ingest a new command into the history"""
    # Rate limiting: 1000 requests per minute per user
    allowed, remaining = rate_limiter.is_allowed(
        f"api_commands:{current_user.id}", max_requests=1000, window_seconds=60
    )
    if not allowed:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please slow down."
        )

    # Get or create host (scoped to current user)
    host = (
        db.query(Host)
        .filter(Host.hostname == cmd.hostname, Host.user_id == current_user.id)
        .first()
    )
    if not host:
        host = Host(hostname=cmd.hostname, user_id=current_user.id)
        db.add(host)
        db.commit()
        db.refresh(host)
    else:
        host.last_seen = datetime.utcnow()
        db.commit()

    # Create command record (redaction is now done client-side)
    db_command = Command(
        command=cmd.command,
        hostname=cmd.hostname,
        username=cmd.username,
        alt_username=cmd.alt_username,
        cwd=cmd.cwd,
        old_pwd=cmd.old_pwd,
        exit_code=cmd.exit_code,
        session_id=cmd.session_id,
        redacted=cmd.redacted,
        host_id=host.id,
        user_id=current_user.id,
    )

    db.add(db_command)
    db.commit()
    db.refresh(db_command)

    # Index in search service
    search_service.index_command(db_command)

    return db_command


@router.get("/")
async def search_commands(  # type: ignore[no-untyped-def]
    q: str | None = None,
    hostname: str | None = None,
    username: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    exit_code: int | None = None,
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):  # Return type omitted: FastAPI/Pydantic can't serialize SQLAlchemy objects in dict
    """Search command history (filtered to current user's commands)"""
    # If search query, use search service
    if q:
        search_results = search_service.search(
            query=q,
            user_id=str(current_user.id),
            filters={
                "hostname": hostname,
                "username": username,
                "exit_code": exit_code,
            },
            limit=page_size,
            offset=page * page_size,
        )

        # Convert timestamp strings in hits back to datetime objects for template compatibility
        hits = search_results.get("hits", [])
        total = search_results.get("total", 0)

        for hit in hits:
            if isinstance(hit.get("timestamp"), str):
                try:
                    hit["timestamp"] = datetime.fromisoformat(
                        hit["timestamp"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

        return {
            "items": hits,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page + 1) * page_size < total,
        }

    # Otherwise, use database query (filtered by user)
    query = db.query(Command).filter(Command.user_id == current_user.id)

    if hostname:
        query = query.filter(Command.hostname == hostname)
    if username:
        query = query.filter(Command.username == username)
    if start_date:
        query = query.filter(Command.timestamp >= start_date)
    if end_date:
        query = query.filter(Command.timestamp <= end_date)
    if exit_code is not None:
        query = query.filter(Command.exit_code == exit_code)

    total = query.count()
    commands = (
        query.order_by(desc(Command.timestamp))
        .offset(page * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": commands,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page + 1) * page_size < total,
    }


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command(
    command_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommandResponse:
    """Get a single command by ID (must belong to current user)"""
    command: Command | None = (
        db.query(Command)
        .filter(Command.id == command_id, Command.user_id == current_user.id)
        .first()
    )
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    return command


@router.delete("/{command_id}")
async def delete_command(
    command_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a command by ID (must belong to current user)"""
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
    return {"message": "Command deleted successfully"}

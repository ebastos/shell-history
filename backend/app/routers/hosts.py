"""Host management endpoints"""

from uuid import UUID

from app.database import get_db
from app.models import Host, User
from app.schemas import HostCreate, HostResponse
from app.services.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("/")
async def list_hosts(  # type: ignore[no-untyped-def]
    active_only: bool = False,
    page: int = 0,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):  # Return type omitted: FastAPI/Pydantic can't serialize SQLAlchemy objects in dict
    """List all registered hosts (filtered to current user's hosts)"""
    query = db.query(Host).filter(Host.user_id == current_user.id)
    if active_only:
        query = query.filter(Host.is_active)

    total = query.count()
    hosts = query.offset(page * page_size).limit(page_size).all()

    return {
        "items": hosts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page + 1) * page_size < total,
    }


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(
    host_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostResponse:
    """Get a host by ID (must belong to current user)"""
    host: Host | None = (
        db.query(Host)
        .filter(Host.id == host_id, Host.user_id == current_user.id)
        .first()
    )
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.post("/", response_model=HostResponse)
async def create_host(
    host: HostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostResponse:
    """Register a new host (for current user)"""
    # Check if host already exists for this user
    existing = (
        db.query(Host)
        .filter(Host.hostname == host.hostname, Host.user_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Host already registered")

    db_host = Host(**host.model_dump(), user_id=current_user.id)
    db.add(db_host)
    db.commit()
    db.refresh(db_host)
    return db_host


@router.put("/{host_id}/deactivate")
async def deactivate_host(
    host_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Deactivate a host (must belong to current user)"""
    host = (
        db.query(Host)
        .filter(Host.id == host_id, Host.user_id == current_user.id)
        .first()
    )
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    host.is_active = False
    db.commit()
    return {"message": "Host deactivated"}

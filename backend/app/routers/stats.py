"""Statistics endpoints"""

import os

from app.database import get_db
from app.models import Command, Host, User
from app.services.auth import get_current_user
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/")
async def get_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, int | str]:
    """Get statistics for current user"""
    total_commands = (
        db.query(Command).filter(Command.user_id == current_user.id).count()
    )
    active_hosts = (
        db.query(Host).filter(Host.user_id == current_user.id, Host.is_active).count()
    )

    # Calculate storage used (this is still global, but could be per-user in future)
    db_path = "/app/data/history.db"
    storage_used = "0 B"
    if os.path.exists(db_path):
        size_bytes = os.path.getsize(db_path)
        if size_bytes < 1024:
            storage_used = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            storage_used = f"{size_bytes / 1024:.1f} KB"
        else:
            storage_used = f"{size_bytes / (1024 * 1024):.1f} MB"

    return {
        "total_commands": total_commands,
        "active_hosts": active_hosts,
        "storage_used": storage_used,
    }

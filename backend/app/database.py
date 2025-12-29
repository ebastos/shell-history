"""Database connection and session management"""

from collections.abc import Generator
from pathlib import Path
from typing import Any

from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Create database directory if it doesn't exist
db_path = settings.database_url.replace("sqlite:///", "")
if db_path.endswith(".db"):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.database_url
    else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
# Using Any type annotation to satisfy mypy while maintaining runtime compatibility
Base: Any = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

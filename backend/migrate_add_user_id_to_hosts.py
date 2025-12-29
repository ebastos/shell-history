"""Migration script to add user_id to hosts table and backfill data

Run this script once to migrate existing data to multi-tenant model.
Creates a default user for existing hosts/commands if needed.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import User
from sqlalchemy import text


def run_migration() -> None:
    """Run migration to add user_id to hosts"""
    db = SessionLocal()

    try:
        print("Starting migration...")

        # Check if user_id column already exists on hosts
        result = db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='hosts'")
        )
        if result.fetchone():
            # Check if column exists
            result = db.execute(text("PRAGMA table_info(hosts)"))
            columns = [row[1] for row in result.fetchall()]
            if "user_id" in columns:
                print(
                    "user_id column already exists on hosts table. Migration already applied."
                )
                return

        # Create a default user if no users exist
        default_user = db.query(User).first()
        if not default_user:
            print("Creating default user for existing data...")
            import secrets

            default_user = User(
                username="default",
                email="default@localhost",
                role="admin",
                api_key=secrets.token_urlsafe(32),
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            print(f"Created default user: {default_user.id}")

        # Step 1: Add user_id column to hosts (nullable initially)
        print("Adding user_id column to hosts table...")
        db.execute(text("ALTER TABLE hosts ADD COLUMN user_id TEXT"))
        db.commit()

        # Step 2: Backfill user_id for all hosts
        print("Backfilling user_id for existing hosts...")
        db.execute(
            text("UPDATE hosts SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": str(default_user.id)},
        )
        db.commit()

        # Step 3: Drop old unique constraint on hostname
        print("Dropping old unique constraint...")
        # SQLite doesn't support dropping constraints directly
        # We'll recreate the table with new schema
        db.execute(
            text(
                "CREATE TABLE hosts_new ("
                "id TEXT PRIMARY KEY, "
                "hostname TEXT NOT NULL, "
                "ip_address TEXT, "
                "os_type TEXT, "
                "is_active BOOLEAN DEFAULT 1, "
                "last_seen TIMESTAMP, "
                "user_id TEXT NOT NULL, "
                "FOREIGN KEY(user_id) REFERENCES users(id), "
                "UNIQUE(hostname, user_id))"
            )
        )

        # Copy data
        db.execute(
            text(
                "INSERT INTO hosts_new SELECT id, hostname, ip_address, os_type, is_active, last_seen, user_id FROM hosts"
            )
        )

        # Drop old table and rename
        db.execute(text("DROP TABLE hosts"))
        db.execute(text("ALTER TABLE hosts_new RENAME TO hosts"))

        # Recreate indexes
        db.execute(text("CREATE INDEX ix_hosts_hostname ON hosts(hostname)"))
        db.execute(text("CREATE INDEX ix_hosts_user_id ON hosts(user_id)"))

        db.commit()

        # Step 4: Backfill user_id for commands that don't have it
        print("Backfilling user_id for existing commands...")
        db.execute(
            text("UPDATE commands SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": str(default_user.id)},
        )
        db.commit()

        print("Migration completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()

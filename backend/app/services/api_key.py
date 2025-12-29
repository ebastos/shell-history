"""API key hashing and verification service"""

import bcrypt
from app.services.password import hash_password


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt.

    Args:
        api_key: Plain text API key

    Returns:
        Hashed API key string
    """
    # Use the same password hashing function
    return hash_password(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against a hash.

    Args:
        plain_key: Plain text API key to verify
        hashed_key: Hashed API key to check against

    Returns:
        True if key matches, False otherwise
    """
    try:
        password_bytes = plain_key.encode("utf-8")
        hash_bytes = hashed_key.encode("utf-8")
        result = bcrypt.checkpw(password_bytes, hash_bytes)
        return bool(result)
    except Exception:
        return False

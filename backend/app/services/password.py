"""Password hashing service using bcrypt directly"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string (bcrypt hash)

    Raises:
        ValueError: If password exceeds bcrypt's 72-byte limit
    """
    # Convert password to bytes
    password_bytes = password.encode("utf-8")
    # Generate salt and hash (rounds=12 is a good default)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return str(hashed.decode("utf-8"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        result = bcrypt.checkpw(password_bytes, hash_bytes)
        return bool(result)
    except Exception:
        return False

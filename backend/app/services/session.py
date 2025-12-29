"""Session management using signed cookies"""

from uuid import UUID

from app.config import settings
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner


class SessionManager:
    """Manages user sessions using signed cookies"""

    def __init__(self, secret_key: str) -> None:
        """Initialize session manager with secret key.

        Args:
            secret_key: Secret key for signing cookies
        """
        self.signer = TimestampSigner(secret_key)
        self.expire_hours = settings.session_expire_hours

    def create_session(self, user_id: UUID) -> str:
        """Create a signed session token for a user.

        Args:
            user_id: User ID to create session for

        Returns:
            Signed session token string
        """
        signed = self.signer.sign(str(user_id))
        return str(signed.decode("utf-8"))

    def verify_session(self, session_token: str) -> UUID | None:
        """Verify and extract user ID from session token.

        Args:
            session_token: Signed session token

        Returns:
            User ID if valid, None otherwise
        """
        try:
            # Unsign with max_age in seconds
            user_id_str = self.signer.unsign(
                session_token.encode("utf-8"), max_age=self.expire_hours * 3600
            )
            return UUID(user_id_str.decode("utf-8"))
        except (BadSignature, SignatureExpired, ValueError):
            return None


# Create global session manager instance
session_manager = SessionManager(settings.secret_key)

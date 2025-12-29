"""CSRF protection service"""

import secrets

from app.config import settings
from itsdangerous import BadSignature, TimestampSigner


class CSRFService:
    """Manages CSRF tokens"""

    def __init__(self, secret_key: str) -> None:
        """Initialize CSRF service with secret key.

        Args:
            secret_key: Secret key for signing CSRF tokens
        """
        self.signer = TimestampSigner(secret_key)

    def generate_token(self) -> str:
        """Generate a new CSRF token.

        Returns:
            Signed CSRF token
        """
        token = secrets.token_urlsafe(32)
        signed = self.signer.sign(token)
        return str(signed.decode("utf-8"))

    def verify_token(self, token: str) -> bool:
        """Verify a CSRF token.

        Args:
            token: CSRF token to verify

        Returns:
            True if token is valid, False otherwise
        """
        if not token:
            return False

        try:
            self.signer.unsign(token.encode("utf-8"), max_age=3600)  # 1 hour expiry
            return True
        except BadSignature:
            return False


# Global CSRF service instance
csrf_service = CSRFService(settings.secret_key)

"""Flash message service for one-time messages"""

import json

from app.config import settings
from itsdangerous import BadSignature, TimestampSigner


class FlashService:
    """Manages flash messages stored in signed cookies"""

    def __init__(self, secret_key: str) -> None:
        """Initialize flash service with secret key.

        Args:
            secret_key: Secret key for signing flash messages
        """
        self.signer = TimestampSigner(secret_key)

    def set_flash(self, message: str, category: str = "info") -> str:
        """Create a signed flash message cookie value.

        Args:
            message: Message text
            category: Message category (info, success, error, warning)

        Returns:
            Signed cookie value
        """
        data = {"message": message, "category": category}
        signed = self.signer.sign(json.dumps(data))
        return str(signed.decode("utf-8"))

    def get_flash(self, cookie_value: str | None) -> tuple[str, str] | None:
        """Extract and verify flash message from cookie.

        Args:
            cookie_value: Signed cookie value

        Returns:
            Tuple of (message, category) if valid, None otherwise
        """
        if not cookie_value:
            return None

        try:
            data_str = self.signer.unsign(
                cookie_value.encode("utf-8"),
                max_age=300,  # 5 minute expiry
            )
            data = json.loads(data_str.decode("utf-8"))
            return (data.get("message", ""), data.get("category", "info"))
        except (BadSignature, ValueError, json.JSONDecodeError):
            return None


# Global flash service instance
flash_service = FlashService(settings.secret_key)

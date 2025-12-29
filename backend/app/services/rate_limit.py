"""Rate limiting service"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self) -> None:
        """Initialize rate limiter with empty storage"""
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check if a request is allowed under rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., IP address)
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        cutoff = now - window_seconds

        # Clean old requests
        requests = self._requests[key]
        requests[:] = [req_time for req_time in requests if req_time > cutoff]

        # Check limit
        if len(requests) >= max_requests:
            return False, 0

        # Add current request
        requests.append(now)
        remaining = max(0, max_requests - len(requests))

        return True, remaining

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests without incrementing counter.

        Args:
            key: Unique identifier for the rate limit
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            Number of remaining requests
        """
        now = time.time()
        cutoff = now - window_seconds

        requests = self._requests[key]
        requests[:] = [req_time for req_time in requests if req_time > cutoff]

        return max(0, max_requests - len(requests))


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: "Request") -> str:
    """Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address as string
    """
    # Check for forwarded IP (from reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain
        return str(forwarded.split(",")[0].strip())

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return str(real_ip.strip())

    # Fallback to direct client
    if request.client:
        return str(request.client.host)

    return "unknown"

"""Exception types for the Township Canada SDK."""

from __future__ import annotations

from typing import Optional


class TownshipCanadaError(Exception):
    """Base exception for all Township Canada SDK errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(TownshipCanadaError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class NotFoundError(TownshipCanadaError):
    """Raised when no results are found (HTTP 404)."""


class ValidationError(TownshipCanadaError):
    """Raised when the request is invalid (HTTP 400)."""


class RateLimitError(TownshipCanadaError):
    """Raised when the rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = 429,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class PayloadTooLargeError(TownshipCanadaError):
    """Raised when the batch payload exceeds 100 items (HTTP 413)."""


class ServerError(TownshipCanadaError):
    """Raised on server-side errors (HTTP 5xx)."""

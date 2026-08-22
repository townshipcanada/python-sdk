"""Exception types for the Township Canada SDK."""

from __future__ import annotations

from typing import Optional


class TownshipCanadaError(Exception):
    """Base exception for all Township Canada SDK errors.

    ``code`` carries the machine-readable error code the Ag and Energy APIs
    return in v1 error bodies (``{"error": {"code", "message"}}``), e.g.
    ``invalid_parameter``, ``invalid_legal_location``, ``bc_not_supported``,
    ``not_found``, ``rate_limit_exceeded``. It is ``None`` for endpoints
    that do not send one.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
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
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, code=code)
        self.retry_after = retry_after


class PayloadTooLargeError(TownshipCanadaError):
    """Raised when the batch payload exceeds 100 items (HTTP 413)."""


class ServerError(TownshipCanadaError):
    """Raised on server-side errors (HTTP 5xx)."""

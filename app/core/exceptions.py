import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class BaseAPIException(HTTPException):
    """Base exception for all API exceptions."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict[str, Any] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class UnauthorizedException(BaseAPIException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(BaseAPIException):
    """Raised when user doesn't have permission."""

    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotFoundException(BaseAPIException):
    """Raised when resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class ConflictException(BaseAPIException):
    """Raised when there's a conflict (e.g., duplicate resource)."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class ValidationException(BaseAPIException):
    """Raised when validation fails."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class RateLimitException(BaseAPIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"},
        )


class InternalServerException(BaseAPIException):
    """Raised for internal server errors."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


# Exception handlers for FastAPI
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    # Convert errors to JSON-serializable format
    errors = exc.errors()
    serializable_errors = []
    for error in errors:
        serializable_error = {}
        for key, value in error.items():
            # Convert any non-serializable objects to strings
            try:
                # Try to serialize to check if it's JSON-serializable
                import json

                json.dumps(value)
                serializable_error[key] = value
            except (TypeError, ValueError):
                # If not serializable, convert to string
                serializable_error[key] = str(value)
        serializable_errors.append(serializable_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": serializable_errors,
            "request_id": (
                request.state.request_id if hasattr(request.state, "request_id") else None
            ),
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors (e.g., unique constraint violations)."""
    logger.error(f"Database integrity error: {exc}")

    # Parse error message to provide user-friendly feedback
    error_msg = str(exc.orig)
    if "unique constraint" in error_msg.lower():
        detail = "A record with this information already exists."
    elif "foreign key constraint" in error_msg.lower():
        detail = "Referenced resource does not exist."
    else:
        detail = "Database constraint violation."

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Conflict",
            "detail": detail,
            "request_id": (
                request.state.request_id if hasattr(request.state, "request_id") else None
            ),
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": (
                request.state.request_id if hasattr(request.state, "request_id") else None
            ),
        },
    )

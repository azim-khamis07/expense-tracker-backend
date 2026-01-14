"""Unit tests for exception handlers."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InternalServerException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    ValidationException,
    general_exception_handler,
    integrity_error_handler,
    validation_exception_handler,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException("Test validation error")
        assert "Test validation error" in str(exc)
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_unauthorized_exception(self):
        """Test UnauthorizedException."""
        exc = UnauthorizedException("Test unauthorized error")
        assert "Test unauthorized error" in str(exc)
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forbidden_exception(self):
        """Test ForbiddenException."""
        exc = ForbiddenException("Test forbidden error")
        assert "Test forbidden error" in str(exc)
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException("Test not found error")
        assert "Test not found error" in str(exc)
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_conflict_exception(self):
        """Test ConflictException."""
        exc = ConflictException("Test conflict error")
        assert "Test conflict error" in str(exc)
        assert exc.status_code == status.HTTP_409_CONFLICT

    def test_rate_limit_exception(self):
        """Test RateLimitException."""
        exc = RateLimitException("Test rate limit error")
        assert "Test rate limit error" in str(exc)
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_internal_server_exception(self):
        """Test InternalServerException."""
        exc = InternalServerException("Test internal error")
        assert "Test internal error" in str(exc)
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestExceptionHandlers:
    """Test exception handler functions."""

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self):
        """Test validation exception handler with RequestValidationError."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-request-id"

        # Create a RequestValidationError with validation errors
        errors = [
            {"loc": ("body", "email"), "msg": "field required", "type": "value_error.missing"}
        ]
        exc = RequestValidationError(errors=errors)

        response = await validation_exception_handler(request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_integrity_error_handler_unique_violation(self):
        """Test integrity error handler for unique constraint violation."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-request-id"

        # Create an IntegrityError
        orig_exc = Exception("duplicate key value violates unique constraint")
        orig_exc.pgcode = "23505"  # Unique violation code
        exc = IntegrityError(statement="INSERT INTO users", params={}, orig=orig_exc)

        response = await integrity_error_handler(request, exc)

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_integrity_error_handler_foreign_key(self):
        """Test integrity error handler for foreign key violation."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-request-id"

        orig_exc = Exception("foreign key constraint")
        orig_exc.pgcode = "23503"  # Foreign key violation code
        exc = IntegrityError(statement="INSERT INTO transactions", params={}, orig=orig_exc)

        response = await integrity_error_handler(request, exc)

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test general exception handler."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-request-id"
        exc = ValueError("Test error")

        response = await general_exception_handler(request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_integrity_error_handler_other_error(self):
        """Test integrity error handler for other constraint violations."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-request-id"

        exc = IntegrityError(
            statement="INSERT INTO table", params={}, orig=Exception("other constraint violation")
        )
        exc.orig.pgcode = "23514"  # Check constraint violation

        response = await integrity_error_handler(request, exc)

        assert response.status_code == status.HTTP_409_CONFLICT

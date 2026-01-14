"""Unit tests for FastAPI dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from jose import JWTError

from app.core.dependencies import (
    get_current_user,
    get_current_verified_user,
    get_optional_current_user,
)
from app.core.exceptions import UnauthorizedException
from app.models.user import User


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful user retrieval."""
        mock_user = User(
            id="user123",
            email="test@example.com",
            password_hash="hashed",
            is_active=True,
            is_email_verified=True,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user123", "type": "access"}

            result = await get_current_user(mock_credentials, mock_db)

            assert result == mock_user
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_type(self):
        """Test invalid token type raises exception."""
        mock_db = AsyncMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user123", "type": "refresh"}

            with pytest.raises(UnauthorizedException, match="Invalid token type"):
                await get_current_user(mock_credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_user_id(self):
        """Test missing user ID in token raises exception."""
        mock_db = AsyncMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = {"type": "access"}

            with pytest.raises(UnauthorizedException, match="missing user ID"):
                await get_current_user(mock_credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_jwt_error(self):
        """Test JWT error raises exception."""
        mock_db = AsyncMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.side_effect = JWTError("Invalid token")

            with pytest.raises(UnauthorizedException, match="Could not validate credentials"):
                await get_current_user(mock_credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self):
        """Test user not found raises exception."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user123", "type": "access"}

            with pytest.raises(UnauthorizedException, match="User not found"):
                await get_current_user(mock_credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self):
        """Test inactive user raises exception."""
        mock_user = User(
            id="user123",
            email="test@example.com",
            password_hash="hashed",
            is_active=False,
            is_email_verified=True,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user123", "type": "access"}

            with pytest.raises(UnauthorizedException, match="User account is inactive"):
                await get_current_user(mock_credentials, mock_db)


class TestGetCurrentVerifiedUser:
    """Test get_current_verified_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_verified_user_success(self):
        """Test successful verified user retrieval."""
        mock_user = User(
            id="user123",
            email="test@example.com",
            password_hash="hashed",
            is_active=True,
            is_email_verified=True,
        )

        result = await get_current_verified_user(mock_user)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_verified_user_not_verified(self):
        """Test unverified user raises exception."""
        mock_user = User(
            id="user123",
            email="test@example.com",
            password_hash="hashed",
            is_active=True,
            is_email_verified=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_verified_user(mock_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Email not verified" in exc_info.value.detail


class TestGetOptionalCurrentUser:
    """Test get_optional_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_optional_current_user_no_credentials(self):
        """Test no credentials returns None."""
        mock_db = AsyncMock()

        result = await get_optional_current_user(None, mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_current_user_valid(self):
        """Test valid credentials returns user."""
        mock_user = User(
            id="user123",
            email="test@example.com",
            password_hash="hashed",
            is_active=True,
            is_email_verified=True,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user123", "type": "access"}

            result = await get_optional_current_user(mock_credentials, mock_db)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_optional_current_user_invalid_returns_none(self):
        """Test invalid credentials returns None."""
        mock_db = AsyncMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        with patch("app.core.dependencies.decode_token") as mock_decode:
            mock_decode.side_effect = JWTError("Invalid token")

            result = await get_optional_current_user(mock_credentials, mock_db)

            assert result is None

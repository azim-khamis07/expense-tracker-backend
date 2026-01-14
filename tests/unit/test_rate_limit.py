"""Unit tests for rate limiting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import RateLimitException
from app.core.rate_limit import (
    check_rate_limit,
    rate_limit_by_ip,
    rate_limit_by_user,
)
from app.infra.redis import redis_client


class TestCheckRateLimit:
    """Test rate limit checking."""

    @pytest.mark.asyncio
    async def test_rate_limit_not_exceeded(self):
        """Test when rate limit is not exceeded."""
        with (
            patch.object(redis_client, "redis", MagicMock()),
            patch.object(redis_client, "increment", new_callable=AsyncMock) as mock_increment,
            patch.object(redis_client, "expire", new_callable=AsyncMock),
        ):
            mock_increment.return_value = 5  # Current count

            # Should not raise
            await check_rate_limit("test:key", max_requests=10, window_seconds=60)

            mock_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test when rate limit is exceeded."""
        with (
            patch.object(redis_client, "redis", MagicMock()),
            patch.object(redis_client, "increment", new_callable=AsyncMock) as mock_increment,
            patch.object(redis_client, "expire", new_callable=AsyncMock),
        ):
            mock_increment.return_value = 11  # Exceeds limit

            with pytest.raises(RateLimitException):
                await check_rate_limit("test:key", max_requests=10, window_seconds=60)

    @pytest.mark.asyncio
    async def test_rate_limit_at_threshold(self):
        """Test when rate limit is exactly at threshold."""
        with (
            patch.object(redis_client, "redis", MagicMock()),
            patch.object(redis_client, "increment", new_callable=AsyncMock) as mock_increment,
            patch.object(redis_client, "expire", new_callable=AsyncMock),
        ):
            mock_increment.return_value = 10  # Exactly at limit

            # Should not raise (limit is >, not >=)
            await check_rate_limit("test:key", max_requests=10, window_seconds=60)

    @pytest.mark.asyncio
    async def test_rate_limit_redis_error(self):
        """Test rate limiting when Redis fails."""
        with (
            patch.object(redis_client, "redis", MagicMock()),
            patch.object(
                redis_client,
                "increment",
                new_callable=AsyncMock,
                side_effect=Exception("Redis error"),
            ),
        ):
            # Should fail open - allow request
            # In production, you might want to log this
            try:
                await check_rate_limit("test:key", max_requests=10, window_seconds=60)
            except (RateLimitException, HTTPException):
                pytest.fail("Should not raise when Redis fails (fail open)")


class TestRateLimitByIP:
    """Test IP-based rate limiting."""

    @pytest.mark.asyncio
    @patch("app.core.rate_limit.check_rate_limit")
    async def test_rate_limit_by_ip_normal(self, mock_check):
        """Test normal rate limiting."""
        mock_settings = MagicMock()
        mock_settings.DISABLE_RATE_LIMITS_IN_TEST = False
        mock_settings.TEST_MODE = False
        mock_settings.RATE_LIMIT_MULTIPLIER = 1.0

        with patch("app.core.config.settings", mock_settings):
            mock_request = MagicMock()
            mock_request.client.host = "192.168.1.1"
            mock_request.url.path = "/api/v1/test"

            dependency = rate_limit_by_ip(max_requests=10, window_seconds=60)
            await dependency(mock_request)

            mock_check.assert_called_once()
            call_args = mock_check.call_args[0]
            assert "192.168.1.1" in call_args[0]  # Key contains IP

    @pytest.mark.asyncio
    @patch("app.core.rate_limit.check_rate_limit")
    async def test_rate_limit_by_ip_disabled_in_test(self, mock_check):
        """Test rate limiting disabled in test mode."""
        mock_settings = MagicMock()
        mock_settings.DISABLE_RATE_LIMITS_IN_TEST = True
        mock_settings.TEST_MODE = True

        with patch("app.core.config.settings", mock_settings):
            mock_request = MagicMock()
            dependency = rate_limit_by_ip(max_requests=10, window_seconds=60)
            await dependency(mock_request)

            # Should not call check_rate_limit
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.core.rate_limit.check_rate_limit")
    async def test_rate_limit_by_ip_multiplier(self, mock_check):
        """Test rate limit multiplier in test mode."""
        mock_settings = MagicMock()
        mock_settings.DISABLE_RATE_LIMITS_IN_TEST = False
        mock_settings.TEST_MODE = True
        mock_settings.RATE_LIMIT_MULTIPLIER = 10.0

        with patch("app.core.config.settings", mock_settings):
            mock_request = MagicMock()
            mock_request.client.host = "192.168.1.1"
            mock_request.url.path = "/api/v1/test"

            dependency = rate_limit_by_ip(max_requests=10, window_seconds=60)
            await dependency(mock_request)

            mock_check.assert_called_once()
            # Should use multiplied limit (10 * 10 = 100)
            call_args = mock_check.call_args[0]
            assert call_args[1] == 100  # max_requests should be 100

    @pytest.mark.asyncio
    @patch("app.core.rate_limit.check_rate_limit")
    async def test_rate_limit_by_ip_unknown_client(self, mock_check):
        """Test rate limiting with unknown client IP."""
        mock_settings = MagicMock()
        mock_settings.DISABLE_RATE_LIMITS_IN_TEST = False
        mock_settings.TEST_MODE = False

        with patch("app.core.config.settings", mock_settings):
            mock_request = MagicMock()
            mock_request.client = None  # No client info

            dependency = rate_limit_by_ip(max_requests=10, window_seconds=60)
            await dependency(mock_request)

            mock_check.assert_called_once()
            call_args = mock_check.call_args[0]
            assert "unknown" in call_args[0]  # Key contains "unknown"


class TestRateLimitByUser:
    """Test user-based rate limiting."""

    @pytest.mark.asyncio
    @patch("app.core.rate_limit.check_rate_limit")
    async def test_rate_limit_by_user(self, mock_check):
        """Test user-based rate limiting."""
        await rate_limit_by_user(
            user_id="user123",
            endpoint="/api/v1/test",
            max_requests=100,
            window_seconds=60,
        )

        mock_check.assert_called_once()
        call_args = mock_check.call_args[0]
        assert "user123" in call_args[0]  # Key contains user_id
        assert call_args[1] == 100  # max_requests
        assert call_args[2] == 60  # window_seconds

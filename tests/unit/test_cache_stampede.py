"""Unit tests for cache stampede prevention."""

from unittest.mock import AsyncMock, patch

import pytest

from app.infra.cache_stampede import get_or_compute
from app.infra.redis import redis_client


class TestCacheStampede:
    """Test cache stampede prevention."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test when value is in cache."""
        test_value = {"key": "value", "data": 123}

        with patch.object(redis_client, "get_json", return_value=test_value):

            async def compute_fn():
                pytest.fail("Should not call compute function on cache hit")

            result = await get_or_compute("test:key", compute_fn, ttl=300)

            assert result == test_value

    @pytest.mark.asyncio
    async def test_cache_miss_lock_acquired(self):
        """Test cache miss when lock is acquired."""
        computed_value = {"computed": "data"}

        async def compute_fn():
            return computed_value

        with (
            patch.object(redis_client, "get_json", return_value=None),
            patch.object(redis_client, "set_if_not_exists", return_value=True),
            patch.object(redis_client, "set", return_value=True),
            patch.object(redis_client, "set_json", return_value=True),
            patch.object(redis_client, "delete", return_value=1),
        ):
            result = await get_or_compute("test:key", compute_fn, ttl=300)

            assert result == computed_value
            redis_client.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_wait_for_computation(self):
        """Test cache miss when waiting for another process."""
        computed_value = {"computed": "data"}

        async def compute_fn():
            return computed_value

        # Simulate: first check returns None, second check returns value
        get_json_calls = [None, computed_value]

        async def get_json_side_effect(key):
            return get_json_calls.pop(0) if get_json_calls else None

        with (
            patch.object(redis_client, "get_json", side_effect=get_json_side_effect),
            patch.object(redis_client, "set_if_not_exists", return_value=False),
            patch.object(redis_client, "exists", return_value=True),
        ):
            result = await get_or_compute("test:key", compute_fn, ttl=300, lock_timeout=1)

            assert result == computed_value

    @pytest.mark.asyncio
    async def test_cache_miss_timeout(self):
        """Test cache miss with timeout."""
        computed_value = {"timeout": "computed"}

        async def compute_fn():
            return computed_value

        with (
            patch.object(redis_client, "get_json", return_value=None),
            patch.object(redis_client, "set_if_not_exists", return_value=False),
            patch.object(redis_client, "exists", return_value=True),
            patch.object(redis_client, "set_json", return_value=True),
            patch("asyncio.sleep", return_value=None),
        ):
            # Use short timeout for test
            result = await get_or_compute("test:key", compute_fn, ttl=300, lock_timeout=0.1)

            assert result == computed_value

    @pytest.mark.asyncio
    async def test_compute_function_error(self):
        """Test error handling in compute function."""

        async def compute_fn():
            raise ValueError("Compute error")

        with (
            patch.object(redis_client, "get_json", return_value=None),
            patch.object(redis_client, "set_if_not_exists", return_value=True),
            patch.object(redis_client, "set", return_value=True),
            patch.object(redis_client, "delete", return_value=1),
        ):
            with pytest.raises(ValueError, match="Compute error"):
                await get_or_compute("test:key", compute_fn, ttl=300)

    @pytest.mark.asyncio
    async def test_redis_error_cache_read(self):
        """Test Redis error during cache read."""
        computed_value = {"computed": "data"}

        async def compute_fn():
            return computed_value

        # get_json returns None on error (as per redis_client implementation)
        # So we should test that None is handled correctly
        with (
            patch.object(redis_client, "get_json", new_callable=AsyncMock, return_value=None),
            patch.object(
                redis_client, "set_if_not_exists", new_callable=AsyncMock, return_value=True
            ),
            patch.object(redis_client, "set", new_callable=AsyncMock, return_value=True),
            patch.object(redis_client, "set_json", new_callable=AsyncMock, return_value=True),
            patch.object(redis_client, "delete", new_callable=AsyncMock, return_value=1),
        ):
            result = await get_or_compute("test:key", compute_fn, ttl=300)

            # Should compute when cache returns None
            assert result == computed_value

    @pytest.mark.asyncio
    async def test_redis_error_lock_acquisition(self):
        """Test Redis error during lock acquisition."""
        computed_value = {"computed": "data"}

        async def compute_fn():
            return computed_value

        # set_if_not_exists returns False on error (as per redis_client implementation)
        # When lock acquisition fails, it goes to the else branch (wait for computation)
        # But since there's no one computing, it will timeout and compute itself
        with (
            patch.object(redis_client, "get_json", new_callable=AsyncMock, return_value=None),
            patch.object(
                redis_client, "set_if_not_exists", new_callable=AsyncMock, return_value=False
            ),
            patch.object(redis_client, "exists", new_callable=AsyncMock, return_value=False),
            patch.object(redis_client, "set_json", new_callable=AsyncMock, return_value=True),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await get_or_compute("test:key", compute_fn, ttl=300, lock_timeout=0.1)

            # Should compute when lock acquisition fails
            assert result == computed_value

    @pytest.mark.asyncio
    async def test_cache_set_error(self):
        """Test error when setting cache value."""
        computed_value = {"computed": "data"}

        async def compute_fn():
            return computed_value

        # set_json returns False on error (as per redis_client implementation)
        # Should still return computed value even if cache fails
        with (
            patch.object(redis_client, "get_json", new_callable=AsyncMock, return_value=None),
            patch.object(
                redis_client, "set_if_not_exists", new_callable=AsyncMock, return_value=True
            ),
            patch.object(redis_client, "set", new_callable=AsyncMock, return_value=True),
            patch.object(redis_client, "set_json", new_callable=AsyncMock, return_value=False),
            patch.object(redis_client, "delete", new_callable=AsyncMock, return_value=1),
        ):
            result = await get_or_compute("test:key", compute_fn, ttl=300)

            # Should still return computed value even if cache fails
            assert result == computed_value

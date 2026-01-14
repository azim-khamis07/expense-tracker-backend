"""Unit tests for Redis client."""

import json
from unittest.mock import AsyncMock

import pytest

from app.infra.redis import RedisClient


class TestRedisClient:
    """Test Redis client operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis connection."""
        return AsyncMock()

    @pytest.fixture
    def redis_client_instance(self, mock_redis):
        """Create RedisClient instance with mocked connection."""
        client = RedisClient()
        client.redis = mock_redis
        return client

    @pytest.mark.asyncio
    async def test_get(self, redis_client_instance, mock_redis):
        """Test GET operation."""
        mock_redis.get.return_value = "test_value"

        result = await redis_client_instance.get("test_key")

        assert result == "test_value"
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_none(self, redis_client_instance, mock_redis):
        """Test GET when key doesn't exist."""
        mock_redis.get.return_value = None

        result = await redis_client_instance.get("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_error(self, redis_client_instance, mock_redis):
        """Test GET error handling."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await redis_client_instance.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set(self, redis_client_instance, mock_redis):
        """Test SET operation."""
        mock_redis.set.return_value = True

        result = await redis_client_instance.set("test_key", "test_value", ex=60)

        assert result is True
        mock_redis.set.assert_called_once_with("test_key", "test_value", ex=60)

    @pytest.mark.asyncio
    async def test_set_error(self, redis_client_instance, mock_redis):
        """Test SET error handling."""
        mock_redis.set.side_effect = Exception("Redis error")

        result = await redis_client_instance.set("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete(self, redis_client_instance, mock_redis):
        """Test DELETE operation."""
        mock_redis.delete.return_value = 2

        result = await redis_client_instance.delete("key1", "key2")

        assert result == 2
        mock_redis.delete.assert_called_once_with("key1", "key2")

    @pytest.mark.asyncio
    async def test_delete_error(self, redis_client_instance, mock_redis):
        """Test DELETE error handling."""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await redis_client_instance.delete("test_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_exists(self, redis_client_instance, mock_redis):
        """Test EXISTS operation."""
        mock_redis.exists.return_value = 1

        result = await redis_client_instance.exists("test_key")

        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_client_instance, mock_redis):
        """Test EXISTS when key doesn't exist."""
        mock_redis.exists.return_value = 0

        result = await redis_client_instance.exists("nonexistent_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_json(self, redis_client_instance, mock_redis):
        """Test GET_JSON operation."""
        test_data = {"key": "value", "number": 123}
        mock_redis.get.return_value = json.dumps(test_data)

        result = await redis_client_instance.get_json("test_key")

        assert result == test_data

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, redis_client_instance, mock_redis):
        """Test GET_JSON with invalid JSON."""
        mock_redis.get.return_value = "invalid json{"

        result = await redis_client_instance.get_json("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_json(self, redis_client_instance, mock_redis):
        """Test SET_JSON operation."""
        test_data = {"key": "value", "number": 123}
        mock_redis.set.return_value = True

        result = await redis_client_instance.set_json("test_key", test_data, ex=60)

        assert result is True
        # Verify JSON was serialized
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test_key"
        assert json.loads(call_args[0][1]) == test_data

    @pytest.mark.asyncio
    async def test_set_json_error(self, redis_client_instance, mock_redis):
        """Test SET_JSON error handling."""
        mock_redis.set.side_effect = Exception("Redis error")

        result = await redis_client_instance.set_json("test_key", {"key": "value"})

        assert result is False

    @pytest.mark.asyncio
    async def test_set_if_not_exists(self, redis_client_instance, mock_redis):
        """Test SET_IF_NOT_EXISTS operation."""
        mock_redis.set.return_value = True

        result = await redis_client_instance.set_if_not_exists("test_key", "value", ex=60)

        assert result is True
        mock_redis.set.assert_called_once_with("test_key", "value", ex=60, nx=True)

    @pytest.mark.asyncio
    async def test_increment(self, redis_client_instance, mock_redis):
        """Test INCREMENT operation."""
        mock_redis.incr.return_value = 5

        result = await redis_client_instance.increment("counter_key")

        assert result == 5
        mock_redis.incr.assert_called_once_with("counter_key")

    @pytest.mark.asyncio
    async def test_increment_error(self, redis_client_instance, mock_redis):
        """Test INCREMENT error handling."""
        mock_redis.incr.side_effect = Exception("Redis error")

        result = await redis_client_instance.increment("counter_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_decrement(self, redis_client_instance, mock_redis):
        """Test DECREMENT operation."""
        mock_redis.decr.return_value = 3

        result = await redis_client_instance.decrement("counter_key")

        assert result == 3
        mock_redis.decr.assert_called_once_with("counter_key")

    @pytest.mark.asyncio
    async def test_decrement_error(self, redis_client_instance, mock_redis):
        """Test DECREMENT error handling."""
        mock_redis.decr.side_effect = Exception("Redis error")

        result = await redis_client_instance.decrement("counter_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_expire(self, redis_client_instance, mock_redis):
        """Test EXPIRE operation."""
        mock_redis.expire.return_value = True

        result = await redis_client_instance.expire("test_key", 60)

        assert result is True
        mock_redis.expire.assert_called_once_with("test_key", 60)

    @pytest.mark.asyncio
    async def test_expire_error(self, redis_client_instance, mock_redis):
        """Test EXPIRE error handling."""
        mock_redis.expire.side_effect = Exception("Redis error")

        result = await redis_client_instance.expire("test_key", 60)

        assert result is False

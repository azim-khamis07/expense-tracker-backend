import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with helper methods."""

    def __init__(self):
        self.redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            # Test connection
            await self.redis.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """
        Set key-value pair with optional expiration.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
        """
        try:
            return await self.redis.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    async def get_json(self, key: str) -> Any | None:
        """Get JSON value by key."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key {key}")
                return None
        return None

    async def set_json(self, key: str, value: Any, ex: int | None = None) -> bool:
        """Set JSON value with automatic Decimal to float conversion."""
        try:
            # Convert Decimal objects to float for JSON serialization
            from decimal import Decimal

            def decimal_to_float(obj):
                """Recursively convert Decimal to float."""
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [decimal_to_float(item) for item in obj]
                return obj

            # Convert all Decimals to floats
            serializable_value = decimal_to_float(value)
            json_value = json.dumps(serializable_value)
            return await self.set(key, json_value, ex=ex)
        except TypeError as e:
            logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False

    async def set_if_not_exists(self, key: str, value: str, ex: int | None = None) -> bool:
        """
        Set key only if it doesn't exist (SETNX pattern).
        Used for distributed locks and cache stampede prevention.
        """
        try:
            return await self.redis.set(key, value, ex=ex, nx=True)
        except Exception as e:
            logger.error(f"Redis SETNX error for key {key}: {e}")
            return False

    async def increment(self, key: str) -> int:
        """Increment integer value."""
        try:
            return await self.redis.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0

    async def decrement(self, key: str) -> int:
        """Decrement integer value."""
        try:
            return await self.redis.decr(key)
        except Exception as e:
            logger.error(f"Redis DECR error for key {key}: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client."""
    return redis_client


def cache(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Callable | None = None,
):
    """
    Decorator for caching function results in Redis.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds (default 5 minutes)
        key_builder: Optional function to build cache key from args

    Usage:
        @cache(key_prefix="user", ttl=600)
        async def get_user(user_id: str):
            return await db.query(User).filter(User.id == user_id).first()
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Default: use all args as key
                key_parts = [str(arg) for arg in args] + [f"{k}={v}" for k, v in kwargs.items()]
                cache_key = f"{key_prefix}:{':'.join(key_parts)}"

            # Try to get from cache
            cached_value = await redis_client.get_json(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            logger.debug(f"Cache MISS: {cache_key}")

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                await redis_client.set_json(cache_key, result, ex=ttl)

            return result

        return wrapper

    return decorator


async def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching pattern.

    Args:
        pattern: Redis key pattern (e.g., "user:*", "dash:123:*")

    Returns:
        Number of keys deleted
    """
    try:
        if redis_client.redis is None:
            logger.warning("Redis client not connected")
            return 0

        keys = []
        async for key in redis_client.redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            deleted = await redis_client.delete(*keys)
            logger.info(f"Invalidated {deleted} cache keys matching {pattern}")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
        return 0

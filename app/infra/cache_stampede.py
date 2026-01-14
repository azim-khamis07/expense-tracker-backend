import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.infra.redis import redis_client

logger = logging.getLogger(__name__)


async def get_or_compute(
    cache_key: str,
    compute_fn: Callable[[], Any],
    ttl: int = 300,
    lock_timeout: int = 10,
) -> Any:
    """
    Get value from cache or compute it with stampede prevention.

    Uses distributed lock to ensure only one process computes the value
    when cache misses, preventing thundering herd problem.

    Args:
        cache_key: Redis cache key
        compute_fn: Async function to compute value if not cached
        ttl: Cache TTL in seconds
        lock_timeout: How long to wait for lock in seconds

    Returns:
        Cached or computed value
    """
    # Try to get from cache first
    cached_value = await redis_client.get_json(cache_key)
    if cached_value is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return cached_value

    # Cache miss - acquire lock to compute
    lock_key = f"lock:{cache_key}"
    computing_key = f"computing:{cache_key}"

    # Try to acquire lock
    lock_acquired = await redis_client.set_if_not_exists(
        lock_key,
        "1",
        ex=30,  # Lock expires in 30 seconds
    )

    if lock_acquired:
        # We got the lock - compute the value
        logger.debug(f"Cache MISS: {cache_key} - Computing (lock acquired)")

        try:
            # Mark as computing
            await redis_client.set(computing_key, "1", ex=30)

            # Compute value (catch errors here to prevent cache stampede retries)
            try:
                result = await compute_fn()
            except Exception as e:
                logger.error(
                    f"Error in compute function for cache key {cache_key}: {e}", exc_info=True
                )
                # Re-raise to let caller handle it, but release lock first
                raise

            # Store in cache
            if result is not None:
                await redis_client.set_json(cache_key, result, ex=ttl)

            return result

        finally:
            # Always release lock
            await redis_client.delete(lock_key, computing_key)

    else:
        # Someone else is computing - wait for result
        logger.debug(f"Cache MISS: {cache_key} - Waiting for computation")

        # Poll for result with timeout
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < lock_timeout:
            # Check if computation is done
            cached_value = await redis_client.get_json(cache_key)
            if cached_value is not None:
                logger.debug(f"Received computed value for {cache_key}")
                return cached_value

            # Check if still computing
            is_computing = await redis_client.exists(computing_key)
            if not is_computing:
                # Computation failed or completed without caching
                break

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

        # Timeout or computation failed - compute ourselves
        logger.warning(f"Timeout waiting for {cache_key} - Computing anyway")
        try:
            result = await compute_fn()
        except Exception as e:
            logger.error(
                f"Error computing value after timeout for cache key {cache_key}: {e}", exc_info=True
            )
            # Re-raise to let caller handle it
            raise

        # Try to cache (best effort)
        if result is not None:
            await redis_client.set_json(cache_key, result, ex=ttl)

        return result

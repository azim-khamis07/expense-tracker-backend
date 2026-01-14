import logging

from fastapi import Request

from app.core.exceptions import RateLimitException
from app.infra.redis import redis_client

logger = logging.getLogger(__name__)


async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """
    Check if rate limit is exceeded.

    Uses Redis INCR for atomic counter operations. The key is created
    with an expiration time when it first reaches count 1.

    Args:
        key: Unique identifier for rate limiting (e.g., IP address, user ID)
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds

    Raises:
        RateLimitException: If rate limit exceeded

    Note:
        On Redis errors, this function fails open (allows request) to prevent
        Redis issues from blocking legitimate users.
    """
    rate_limit_key = f"rate_limit:{key}"

    if not redis_client.redis:
        logger.warning("Redis not available, skipping rate limit check")
        return

    try:
        # Atomic increment (creates key with value 1 if doesn't exist)
        count = await redis_client.increment(rate_limit_key)

        # If this is the first request in the window (count == 1), set expiration
        # INCR on non-existent key returns 1, so count == 1 means new key
        if count == 1:
            # Set expiration for the time window
            # This is safe even if called multiple times (idempotent)
            await redis_client.expire(rate_limit_key, window_seconds)

        # Check if rate limit exceeded
        if count > max_requests:
            logger.warning(
                f"Rate limit exceeded for: {key} (count: {count}, max: {max_requests}, window: {window_seconds}s)"
            )
            raise RateLimitException(
                f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
            )

    except RateLimitException:
        # Re-raise rate limit exceptions
        raise
    except Exception as e:
        logger.error(f"Rate limit check failed for {key}: {e}", exc_info=True)
        # On error, allow request (fail open) to prevent Redis issues from blocking users
        return


def rate_limit_by_ip(
    max_requests: int = 60,
    window_seconds: int = 60,
):
    """
    Factory function to create a rate limit dependency by IP address.

    Respects TEST_MODE and DISABLE_RATE_LIMITS_IN_TEST settings.
    In test mode, rate limits can be disabled or multiplied.

    Usage:
        @app.post("/endpoint")
        async def endpoint(
            request: Request,
            _: None = Depends(rate_limit_by_ip(max_requests=10, window_seconds=60))
        ):
            ...
    """
    from app.core.config import settings

    async def rate_limit_dependency(request: Request) -> None:
        # Skip rate limiting in test mode if disabled
        if settings.DISABLE_RATE_LIMITS_IN_TEST and settings.TEST_MODE:
            logger.debug("Rate limiting disabled in test mode")
            return

        # Apply multiplier in test mode
        effective_max_requests = max_requests
        if settings.TEST_MODE and settings.RATE_LIMIT_MULTIPLIER > 1.0:
            effective_max_requests = int(max_requests * settings.RATE_LIMIT_MULTIPLIER)
            logger.debug(
                f"Rate limit multiplied in test mode: {max_requests} -> {effective_max_requests}"
            )

        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        key = f"{endpoint}:{client_ip}"
        await check_rate_limit(key, effective_max_requests, window_seconds)

    return rate_limit_dependency


async def rate_limit_by_user(
    user_id: str,
    endpoint: str,
    max_requests: int = 100,
    window_seconds: int = 60,
) -> None:
    """
    Rate limit by user ID.

    This function should be called within endpoint handlers, not as a dependency.

    Usage:
        @app.post("/create_transaction")
        async def create_transaction(
            request: Request,
            current_user: User = Depends(get_current_user)
        ):
            await rate_limit_by_user(current_user.id, "create_transaction", 10, 60)
            ...
    """
    key = f"{endpoint}:{user_id}"
    await check_rate_limit(key, max_requests, window_seconds)


def create_rate_limit_dependency(max_requests: int = 60, window_seconds: int = 60):
    """
    Factory function to create a rate limit dependency with custom limits.

    Usage:
        strict_rate_limit = create_rate_limit_dependency(max_requests=5, window_seconds=60)

        @app.post("/login")
        async def login(
            request: Request,
            _: None = Depends(strict_rate_limit)
        ):
            ...
    """

    async def rate_limit_dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        key = f"{endpoint}:{client_ip}"
        await check_rate_limit(key, max_requests, window_seconds)

    return rate_limit_dependency

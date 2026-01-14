import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def check_database_health(db: AsyncSession) -> dict:
    """Check database connectivity and performance"""
    try:
        start = time.time()

        result = await db.execute(text("SELECT 1"))
        result.scalar()

        duration = (time.time() - start) * 1000  # ms

        return {"status": "healthy", "response_time_ms": round(duration, 2)}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_redis_health(redis) -> dict:
    """Check Redis connectivity and performance"""
    try:
        start = time.time()

        # Access the underlying redis client
        redis_client = redis.redis if hasattr(redis, "redis") else redis
        await redis_client.ping()

        duration = (time.time() - start) * 1000  # ms

        return {"status": "healthy", "response_time_ms": round(duration, 2)}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_s3_health() -> dict:
    """Check S3 connectivity"""
    try:
        from app.core.config import settings
        from app.infra.s3 import S3Client

        # Skip S3 check if not configured
        if not settings.S3_ENDPOINT_URL and not settings.S3_ACCESS_KEY_ID:
            return {"status": "not_configured", "message": "S3 not configured"}

        start = time.time()
        s3_client = S3Client()

        # Try to list objects (lightweight operation)
        # Note: boto3 client operations are synchronous, so we run in executor
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3_client.s3_client.list_objects_v2(Bucket=s3_client.bucket_name, MaxKeys=1),
        )

        duration = (time.time() - start) * 1000  # ms

        return {"status": "healthy", "response_time_ms": round(duration, 2)}
    except Exception as e:
        logger.error(f"S3 health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def get_system_metrics() -> dict:
    """Get system metrics"""
    try:
        import psutil

        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
    except ImportError:
        logger.warning("psutil not installed, system metrics unavailable")
        return {
            "cpu_percent": None,
            "memory_percent": None,
            "disk_percent": None,
            "error": "psutil not installed",
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {"cpu_percent": None, "memory_percent": None, "disk_percent": None, "error": str(e)}

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.health import (
    check_database_health,
    check_redis_health,
    check_s3_health,
    get_system_metrics,
)
from app.core.metrics import metrics_endpoint
from app.infra.redis import get_redis

router = APIRouter(tags=["Monitoring"])


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    """Detailed health check with all dependencies"""

    db_health = await check_database_health(db)
    redis_health = await check_redis_health(redis)
    s3_health = await check_s3_health()

    overall_status = "healthy"
    if any(service["status"] == "unhealthy" for service in [db_health, redis_health, s3_health]):
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "services": {"database": db_health, "redis": redis_health, "s3": s3_health},
    }


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()


@router.get("/metrics/system")
async def system_metrics_endpoint(db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    """System metrics endpoint (application metrics)"""

    system_metrics = await get_system_metrics()

    # Get database stats
    try:
        from sqlalchemy import text

        result = await db.execute(
            text(
                """
            SELECT
                (SELECT COUNT(*) FROM users) as user_count,
                (SELECT COUNT(*) FROM transactions WHERE deleted_at IS NULL) as transaction_count,
                (SELECT COUNT(*) FROM categories) as category_count,
                (SELECT COUNT(*) FROM report_jobs) as report_count
        """
            )
        )
        stats = result.fetchone()

        db_stats = {
            "users": stats[0] if stats else 0,
            "transactions": stats[1] if stats else 0,
            "categories": stats[2] if stats else 0,
            "reports": stats[3] if stats else 0,
        }
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get database stats: {e}")
        db_stats = {"error": str(e)}

    return {"system": system_metrics, "database": db_stats}

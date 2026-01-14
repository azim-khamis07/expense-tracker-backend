import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import (
    general_exception_handler,
    integrity_error_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.metrics import PrometheusMiddleware
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware, TimingMiddleware
from app.db.session import engine
from app.infra.redis import redis_client

# Import all routers
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.receipts.router import router as receipts_router
from app.modules.reports.router import router as reports_router
from app.modules.tags.router import router as tags_router
from app.modules.transactions.router import router as transactions_router
from app.modules.users.router import router as users_router

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade expense tracking API with receipts and async PDF reports",
    version="0.6.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(PrometheusMiddleware)

# Configure CORS
# Note: CORS middleware must be added before other middleware to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(categories_router, prefix=settings.api_prefix)
app.include_router(tags_router, prefix=settings.api_prefix)
app.include_router(transactions_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(receipts_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(monitoring_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"Starting {settings.APP_NAME} v0.6.0 in {settings.ENVIRONMENT} mode")

    # Initialize Redis
    try:
        await redis_client.connect()
        logger.info("Redis initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}")

    # Close Redis connection
    await redis_client.disconnect()

    # Close database connection
    await engine.dispose()


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint with dependency checks and timeouts."""
    # Check Redis with timeout (1.5 seconds)
    redis_healthy = False
    try:
        if redis_client.redis:
            await asyncio.wait_for(redis_client.redis.ping(), timeout=1.5)
            redis_healthy = True
    except TimeoutError:
        logger.warning("Redis health check timed out")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    # Check Database with timeout (1.5 seconds)
    db_healthy = False
    try:

        async def db_check():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(db_check(), timeout=1.5)
        db_healthy = True
    except TimeoutError:
        logger.warning("Database health check timed out")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Overall status
    overall_status = "healthy" if (redis_healthy and db_healthy) else "degraded"

    return {
        "status": overall_status,
        "environment": settings.ENVIRONMENT,
        "version": "0.6.0",
        "request_id": getattr(request.state, "request_id", None),
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    }


@app.get(f"{settings.api_prefix}/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Welcome to ExpenseTracker API",
        "version": settings.API_VERSION,
        "docs": f"{settings.api_prefix}/docs",
        "features": [
            "Authentication & User Management",
            "Categories & Tags",
            "Transactions with Advanced Filtering",
            "Cursor-based Pagination",
            "Statistics & Analytics",
            "Dashboard with Caching",
            "Time Series & Trends",
            "Tag Analytics",
            "Receipt Upload & Management",
            "S3 Storage with Presigned URLs",
            "Async PDF Report Generation",
            "Celery Background Jobs",
        ],
    }

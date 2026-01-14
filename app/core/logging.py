import logging
import sys

from pythonjsonlogger import jsonlogger  # type: ignore[import]

from app.core.config import settings


def setup_logging():
    """Configure structured logging"""

    logger = logging.getLogger()
    logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        # JSON format for production
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d"
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    return logger

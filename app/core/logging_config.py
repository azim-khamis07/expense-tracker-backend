import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger  # type: ignore[import]

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add custom fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["environment"] = settings.ENVIRONMENT

        # Add request ID if available
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id


def setup_logging() -> None:
    """
    Configure application logging.
    Uses JSON format for structured logging in production.
    """
    # Get log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Use JSON formatter in production, simple formatter in development
    if settings.ENVIRONMENT == "production":
        formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific log levels for libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)

    # Log startup message
    root_logger.info(
        f"Logging configured: level={settings.LOG_LEVEL}, " f"environment={settings.ENVIRONMENT}"
    )

"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "expense_tracker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.modules.reports.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,  # 1 hour
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Task routing
celery_app.conf.task_routes = {
    "app.modules.reports.tasks.*": {"queue": "reports"},
}

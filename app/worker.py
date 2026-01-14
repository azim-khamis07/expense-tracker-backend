"""Celery worker entry point."""

from app.infra.celery_app import celery_app

# Import tasks to register them
from app.modules.reports import tasks  # noqa

if __name__ == "__main__":
    celery_app.worker_main()

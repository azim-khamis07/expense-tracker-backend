"""Repository for report job database operations."""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_job import ReportJob, ReportStatus

logger = logging.getLogger(__name__)


class ReportRepository:
    """Repository for report job operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: str,
        params_json: str,
    ) -> ReportJob:
        """
        Create new report job.

        Args:
            user_id: User ID requesting the report
            params_json: JSON string of report parameters

        Returns:
            Created ReportJob instance
        """
        job = ReportJob(
            user_id=user_id,
            params_json=params_json,
            status=ReportStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        logger.info(f"Created report job: {job.id} for user {user_id}")
        return job

    async def get_by_id(self, job_id: str, user_id: str) -> ReportJob | None:
        """
        Get report by ID (with ownership check).

        Args:
            job_id: Report job ID
            user_id: User ID for ownership verification

        Returns:
            ReportJob if found and owned by user, None otherwise
        """
        result = await self.db.execute(
            select(ReportJob).where(ReportJob.id == job_id, ReportJob.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[ReportJob]:
        """
        List user's reports.

        Args:
            user_id: User ID
            limit: Maximum number of reports to return

        Returns:
            List of ReportJob instances
        """
        result = await self.db.execute(
            select(ReportJob)
            .where(ReportJob.user_id == user_id)
            .order_by(ReportJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        job_id: str,
        status: ReportStatus,
        s3_key: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        """
        Update job status.

        Args:
            job_id: Report job ID
            status: New status
            s3_key: S3 key of generated PDF (if completed)
            error_message: Error message (if failed)
            started_at: When processing started
            finished_at: When processing finished
        """
        values: dict = {
            "status": status,
        }

        if s3_key:
            values["s3_key"] = s3_key
        if error_message:
            values["error_message"] = error_message
        if started_at:
            values["started_at"] = started_at
        elif status == ReportStatus.PROCESSING and not started_at:
            values["started_at"] = datetime.now(UTC)
        if finished_at:
            values["finished_at"] = finished_at
        elif status in (ReportStatus.COMPLETED, ReportStatus.FAILED):
            values["finished_at"] = datetime.now(UTC)

        await self.db.execute(update(ReportJob).where(ReportJob.id == job_id).values(**values))
        await self.db.flush()
        logger.info(f"Updated report job {job_id} status to {status}")

    async def delete(self, job_id: str, user_id: str) -> bool:
        """
        Delete report job.

        Args:
            job_id: Report job ID
            user_id: User ID for ownership verification

        Returns:
            True if deleted, False if not found or not owned by user
        """
        result = await self.db.execute(
            delete(ReportJob).where(ReportJob.id == job_id, ReportJob.user_id == user_id)
        )
        await self.db.flush()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted report job {job_id} for user {user_id}")
        return deleted

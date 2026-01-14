"""Service layer for report operations."""

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.s3 import s3_client
from app.modules.reports.repo import ReportRepository
from app.modules.reports.schemas import (
    ReportListResponse,
    ReportRequest,
    ReportResponse,
    ReportStatus,
)
from app.modules.reports.tasks import generate_report_task

logger = logging.getLogger(__name__)


class ReportService:
    """Service for report operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReportRepository(db)

    async def request_report(
        self,
        user_id: str,
        request: ReportRequest,
    ) -> ReportResponse:
        """
        Request new report generation.

        Args:
            user_id: User ID requesting the report
            request: Report request parameters

        Returns:
            ReportResponse with job details
        """
        # Prepare parameters as JSON
        params = {
            "report_type": request.report_type.value,
            "format": request.format.value,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "include_receipts": request.include_receipts,
            "email_when_ready": request.email_when_ready,
        }
        params_json = json.dumps(params)

        # Create job record
        job = await self.repo.create(
            user_id=user_id,
            params_json=params_json,
        )
        await self.db.commit()

        # Enqueue Celery task
        try:
            generate_report_task.delay(
                str(job.id),
                str(user_id),
                params_json,
            )
            logger.info(f"Enqueued report generation task for job {job.id}")
        except Exception as e:
            logger.error(f"Failed to enqueue report task: {e}")
            # Mark job as failed if task enqueue fails
            await self.repo.update_status(
                job.id,
                ReportStatus.FAILED,
                error_message=f"Failed to start report generation: {str(e)}",
            )
            await self.db.commit()
            raise

        return await self._to_response(job)

    async def get_report_status(
        self,
        job_id: str,
        user_id: str,
    ) -> ReportResponse | None:
        """
        Get report status.

        Args:
            job_id: Report job ID
            user_id: User ID for ownership verification

        Returns:
            ReportResponse if found, None otherwise
        """
        job = await self.repo.get_by_id(job_id, user_id)
        if not job:
            return None
        return await self._to_response(job)

    async def list_reports(
        self,
        user_id: str,
        limit: int = 50,
    ) -> ReportListResponse:
        """
        List user's reports.

        Args:
            user_id: User ID
            limit: Maximum number of reports to return

        Returns:
            ReportListResponse with list of reports
        """
        jobs = await self.repo.get_all_by_user(user_id, limit)
        items = []
        for job in jobs:
            items.append(await self._to_response(job))
        return ReportListResponse(items=items, total=len(items))

    async def delete_report(
        self,
        job_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete report job and S3 file.

        Args:
            job_id: Report job ID
            user_id: User ID for ownership verification

        Returns:
            True if deleted, False otherwise
        """
        # Get job first to access S3 key
        job = await self.repo.get_by_id(job_id, user_id)
        if not job:
            return False

        # Delete S3 file if exists
        if job.s3_key:
            try:
                await s3_client.delete_file(job.s3_key)
                logger.info(f"Deleted S3 file: {job.s3_key}")
            except Exception as e:
                logger.warning(f"Failed to delete S3 file {job.s3_key}: {e}")
                # Continue with DB deletion even if S3 deletion fails

        # Delete database record
        deleted = await self.repo.delete(job_id, user_id)
        await self.db.commit()
        return deleted

    async def get_report_download_url(
        self,
        job_id: str,
        user_id: str,
        expiration: int = 3600,
    ) -> str | None:
        """
        Get presigned download URL for completed report.

        Args:
            job_id: Report job ID
            user_id: User ID for ownership verification
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL if report exists and is completed, None otherwise
        """
        job = await self.repo.get_by_id(job_id, user_id)
        if not job:
            return None

        if job.status != ReportStatus.COMPLETED or not job.s3_key:
            return None

        # Generate presigned URL
        download_url = await s3_client.generate_presigned_url(job.s3_key, expiration)
        return download_url

    async def _to_response(self, job) -> ReportResponse:
        """
        Convert ReportJob model to ReportResponse schema.

        Args:
            job: ReportJob model instance

        Returns:
            ReportResponse schema instance
        """
        # Parse params_json to extract report_type and format
        try:
            params = json.loads(job.params_json) if job.params_json else {}
            report_type = params.get("report_type", "expense_summary")
            format = params.get("format", "pdf")
        except (json.JSONDecodeError, AttributeError):
            report_type = "expense_summary"
            format = "pdf"

        # Generate download URL if completed
        file_url = None
        file_size = None
        if job.status == ReportStatus.COMPLETED and job.s3_key:
            file_url = await s3_client.generate_presigned_url(job.s3_key, expiration=3600)
            # Note: file_size would need to be fetched from S3 metadata or stored
            # For now, we'll leave it as None

        return ReportResponse(
            id=str(job.id),
            user_id=str(job.user_id),
            report_type=report_type,
            format=format,
            status=ReportStatus(job.status.value),
            progress=0,  # Progress not stored in model
            file_url=file_url,
            file_size=file_size,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.finished_at,  # Map finished_at to completed_at
        )

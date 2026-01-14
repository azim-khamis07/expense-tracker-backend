"""Report API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.modules.reports.schemas import (
    ReportListResponse,
    ReportRequest,
    ReportResponse,
)
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request report generation",
    description="Request new report generation (async). Returns job_id immediately; poll /reports/{job_id} for status.",
)
async def request_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request new report generation (async).

    **Returns:** Job ID immediately
    **Status:** Poll `/reports/{job_id}` for status
    **Processing:** Report generation happens asynchronously via Celery
    """
    service = ReportService(db)
    return await service.request_report(current_user.id, request)


@router.get(
    "/{job_id}",
    response_model=ReportResponse,
    summary="Get report status",
    description="Get report generation status and download URL if completed",
)
async def get_report_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get report generation status.

    **Status values:**
    - `pending`: Job queued, waiting to start
    - `processing`: Report generation in progress
    - `completed`: Report ready (download_url available)
    - `failed`: Generation failed (error_message available)
    """
    service = ReportService(db)
    report = await service.get_report_status(job_id, current_user.id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List reports",
    description="List user's reports",
)
async def list_reports(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reports to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's reports.

    Returns reports ordered by creation date (newest first).
    """
    service = ReportService(db)
    return await service.list_reports(current_user.id, limit)


@router.get(
    "/{job_id}/download",
    summary="Get report download URL",
    description="Get presigned download URL for completed report",
)
async def get_report_download(
    job_id: str,
    expiration: int = Query(3600, ge=60, le=86400, description="URL expiration in seconds"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get presigned download URL for completed report.

    **Returns:** Presigned URL valid for specified expiration time
    **Note:** Only works for completed reports
    """
    service = ReportService(db)
    download_url = await service.get_report_download_url(job_id, current_user.id, expiration)
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or not completed",
        )
    return {"download_url": download_url, "expires_in": expiration}


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report",
    description="Delete report job and associated PDF file",
)
async def delete_report(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete report.

    Removes both the database record and the PDF file from S3.
    """
    service = ReportService(db)
    deleted = await service.delete_report(job_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return None

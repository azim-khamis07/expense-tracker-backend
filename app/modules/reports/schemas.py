"""Report schemas for request and response models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ReportFormat(str, Enum):
    """Report file format."""

    PDF = "pdf"
    CSV = "csv"  # Future support


class ReportStatus(str, Enum):
    """Report job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(str, Enum):
    """Report type."""

    EXPENSE_SUMMARY = "expense_summary"
    CATEGORY_BREAKDOWN = "category_breakdown"
    MONTHLY_STATEMENT = "monthly_statement"


class ReportRequest(BaseModel):
    """Request schema for creating a new report."""

    report_type: ReportType = Field(..., description="Type of report to generate")
    format: ReportFormat = Field(default=ReportFormat.PDF, description="Report format")
    start_date: datetime = Field(..., description="Start date for report data")
    end_date: datetime = Field(..., description="End date for report data")
    include_receipts: bool = Field(default=False, description="Include receipt images in report")
    email_when_ready: bool = Field(
        default=False, description="Send email notification when report is ready"
    )

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Validate that end_date is after start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class ReportResponse(BaseModel):
    """Response schema for report job."""

    id: str = Field(..., description="Report job ID")
    user_id: str = Field(..., description="User ID who requested the report")
    report_type: str = Field(..., description="Type of report")
    format: str = Field(..., description="Report format")
    status: ReportStatus = Field(..., description="Current job status")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")
    file_url: str | None = Field(None, description="Download URL for completed report")
    file_size: int | None = Field(None, description="File size in bytes")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="When the report was requested")
    started_at: datetime | None = Field(None, description="When processing started")
    completed_at: datetime | None = Field(None, description="When processing completed")

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Response schema for list of reports."""

    items: list[ReportResponse] = Field(..., description="List of reports")
    total: int = Field(..., description="Total number of reports")

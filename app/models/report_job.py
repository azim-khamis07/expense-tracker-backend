import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReportStatus(str, enum.Enum):
    """Report job status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportJob(Base):
    """Report job model for async PDF generation tracking."""

    __tablename__ = "report_jobs"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Key
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Report parameters (stored as JSON)
    params_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON string of report parameters (start_date, end_date, etc.)",
    )

    # Job status
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus),
        nullable=False,
        default=ReportStatus.PENDING,
        index=True,
    )

    # Result
    s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="S3 key of generated PDF (if completed)"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error message if failed"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="report_jobs")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ReportJob(id={self.id}, status={self.status})>"

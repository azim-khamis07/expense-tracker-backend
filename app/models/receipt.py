from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Receipt(Base):
    """Receipt model for transaction file attachments."""

    __tablename__ = "receipts"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Key
    transaction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One receipt per transaction
        index=True,
    )

    # File metadata
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="S3 object key (path)")
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Original uploaded filename"
    )
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="MIME type (e.g., image/jpeg)"
    )
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="File size in bytes")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(  # type: ignore[name-defined]
        back_populates="receipt", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Receipt(id={self.id}, filename={self.original_filename})>"

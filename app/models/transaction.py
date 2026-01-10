from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tag import transaction_tags


class Transaction(Base):
    """Transaction model for expense and income records."""

    __tablename__ = "transactions"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Transaction data
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False,
        comment="Amount in currency units (e.g., 100.50 = $100.50)",
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD", comment="ISO 4217 currency code"
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="expense or income")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Occurrence timestamp (user's transaction date)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When the transaction actually occurred (UTC)",
    )

    # Soft delete (for audit trail)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft delete timestamp",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Composite indexes and constraints for common queries
    __table_args__ = (
        # Check constraint: amount must be positive (type field indicates expense/income)
        CheckConstraint("amount >= 0", name="ck_transaction_amount_positive"),
        # For listing user's transactions by date
        Index("ix_transactions_user_occurred", "user_id", "occurred_at"),
        # For filtering by category and date
        Index("ix_transactions_user_category_occurred", "user_id", "category_id", "occurred_at"),
        # For filtering by type and date
        Index("ix_transactions_user_type_occurred", "user_id", "type", "occurred_at"),
        # Partial index for active (non-deleted) transactions
        Index(
            "ix_transactions_active",
            "user_id",
            "occurred_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")  # type: ignore[name-defined]
    category: Mapped["Category | None"] = relationship(  # type: ignore[name-defined]
        back_populates="transactions"
    )
    tags: Mapped[list["Tag"]] = relationship(  # type: ignore[name-defined]
        secondary=transaction_tags, back_populates="transactions"
    )
    receipt: Mapped["Receipt | None"] = relationship(  # type: ignore[name-defined]
        back_populates="transaction", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount})>"

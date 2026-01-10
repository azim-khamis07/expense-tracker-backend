from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Junction table for many-to-many relationship between transactions and tags
transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column(
        "transaction_id",
        String(36),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=datetime.utcnow),
)


class Tag(Base):
    """Tag model for flexible transaction categorization."""

    __tablename__ = "tags"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Key
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tag data
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str | None] = mapped_column(
        String(7), nullable=True, comment="Hex color code (e.g., #FF5733)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Unique constraint: user cannot have duplicate tag names
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_tag_name"),)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tags")  # type: ignore[name-defined]
    transactions: Mapped[list["Transaction"]] = relationship(  # type: ignore[name-defined]
        secondary=transaction_tags, back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"

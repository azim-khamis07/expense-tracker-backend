from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    """Category model for organizing transactions."""

    __tablename__ = "categories"

    # Primary Key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign Key
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category data
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="expense or income")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

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

    # Unique constraint: user cannot have duplicate category names
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_category_name"),)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="categories")  # type: ignore[name-defined]
    transactions: Mapped[list["Transaction"]] = relationship(  # type: ignore[name-defined]
        back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, type={self.type})>"

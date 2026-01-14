from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class TransactionType:
    """Transaction type constants."""

    EXPENSE = "expense"
    INCOME = "income"


class TransactionCreate(BaseModel):
    """Schema for creating a transaction."""

    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="ISO 4217 currency code"
    )
    type: str = Field(..., description="Transaction type (expense or income)")
    category_id: str = Field(..., min_length=1, description="Category ID (required)")
    description: str | None = Field(None, max_length=1000, description="Transaction description")
    note: str | None = Field(None, max_length=1000, description="Additional notes")
    occurred_at: datetime = Field(..., description="When transaction occurred (ISO 8601)")
    tag_ids: list[str] = Field(default_factory=list, description="List of tag IDs to attach")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate transaction type."""
        if v not in [TransactionType.EXPENSE, TransactionType.INCOME]:
            raise ValueError(f"Type must be 'expense' or 'income', got: {v}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        return v.upper()

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: str) -> str:
        """Validate category ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Category ID is required and cannot be empty")
        return v.strip()


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""

    amount: Decimal | None = Field(None, gt=0, description="Transaction amount")
    category_id: str | None = Field(None, description="Category ID (use empty string to unset)")
    description: str | None = Field(None, max_length=1000, description="Transaction description")
    note: str | None = Field(None, max_length=1000, description="Additional notes")
    occurred_at: datetime | None = Field(None, description="When transaction occurred")
    tag_ids: list[str] | None = Field(None, description="List of tag IDs (replaces existing tags)")


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    id: str
    user_id: str
    category_id: str | None
    category_name: str | None
    amount: Decimal
    currency: str
    type: str
    description: str | None
    note: str | None
    occurred_at: datetime
    tags: list[dict] = Field(default_factory=list)
    has_receipt: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListFilter(BaseModel):
    """Schema for transaction list filters."""

    start_date: datetime | None = Field(None, description="Start date (inclusive)")
    end_date: datetime | None = Field(None, description="End date (inclusive)")
    category_id: str | None = Field(None, description="Filter by category")
    type: str | None = Field(None, description="Filter by type (expense/income)")
    min_amount: Decimal | None = Field(None, ge=0, description="Minimum amount")
    max_amount: Decimal | None = Field(None, ge=0, description="Maximum amount")
    tag_ids: list[str] | None = Field(
        None, description="Filter by tags (transactions with ANY of these tags)"
    )
    cursor: str | None = Field(None, description="Cursor for pagination")
    limit: int = Field(default=50, ge=1, le=100, description="Number of items per page")


class TransactionPage(BaseModel):
    """Schema for paginated transaction list."""

    data: list[TransactionResponse]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class TransactionStats(BaseModel):
    """Schema for transaction statistics."""

    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    transaction_count: int
    average_transaction: Decimal

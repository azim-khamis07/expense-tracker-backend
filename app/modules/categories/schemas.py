from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CategoryType:
    """Category type constants."""

    EXPENSE = "expense"
    INCOME = "income"


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    type: str = Field(..., description="Category type (expense or income)")
    description: str | None = Field(
        None, max_length=500, description="Optional category description"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate category type."""
        if v not in [CategoryType.EXPENSE, CategoryType.INCOME]:
            raise ValueError(f"Type must be 'expense' or 'income', got: {v}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean category name."""
        return v.strip()


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Category name")
    description: str | None = Field(None, max_length=500, description="Category description")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and clean category name."""
        return v.strip() if v else None


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: str
    user_id: str
    name: str
    type: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    transaction_count: int = Field(default=0, description="Number of transactions in this category")

    class Config:
        from_attributes = True


class CategoryList(BaseModel):
    """Schema for list of categories."""

    items: list[CategoryResponse]
    total: int
    expense_count: int
    income_count: int

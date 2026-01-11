from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TagCreate(BaseModel):
    """Schema for creating a tag."""

    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    color: str | None = Field(
        None, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code (e.g., #FF5733)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean tag name."""
        return v.strip().lower()


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: str | None = Field(None, min_length=1, max_length=50, description="Tag name")
    color: str | None = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and clean tag name."""
        return v.strip().lower() if v else None


class TagResponse(BaseModel):
    """Schema for tag response."""

    id: str
    user_id: str
    name: str
    color: str | None
    created_at: datetime
    transaction_count: int = Field(default=0, description="Number of transactions with this tag")

    class Config:
        from_attributes = True


class TagList(BaseModel):
    """Schema for list of tags."""

    items: list[TagResponse]
    total: int

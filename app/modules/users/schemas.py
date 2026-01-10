import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserProfile(BaseModel):
    """Detailed user profile schema."""

    id: str
    email: str
    is_email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateUserProfile(BaseModel):
    """Schema for updating user profile."""

    email: EmailStr | None = Field(None, description="New email address")


class ChangePasswordRequest(BaseModel):
    """Schema for changing password."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

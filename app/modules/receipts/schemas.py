from datetime import datetime

from pydantic import BaseModel, Field


class ReceiptUploadResponse(BaseModel):
    """Response after uploading receipt."""

    id: str
    transaction_id: str
    original_filename: str
    content_type: str
    size: int
    s3_key: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReceiptResponse(BaseModel):
    """Receipt details with presigned URL."""

    id: str
    transaction_id: str
    original_filename: str
    content_type: str
    size: int
    created_at: datetime
    download_url: str = Field(description="Presigned URL for download (valid for 1 hour)")


class PresignedUploadUrl(BaseModel):
    """Presigned URL for direct client upload."""

    upload_url: str
    fields: dict
    s3_key: str
    expires_in: int = Field(description="URL expiration in seconds")


class ReceiptMetadata(BaseModel):
    """Receipt file metadata."""

    size: int
    content_type: str
    last_modified: datetime

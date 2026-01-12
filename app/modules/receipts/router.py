from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.receipts.schemas import (
    PresignedUploadUrl,
    ReceiptResponse,
    ReceiptUploadResponse,
)
from app.modules.receipts.service import ReceiptService

router = APIRouter(prefix="/transactions", tags=["Receipts"])


@router.post(
    "/{transaction_id}/receipt",
    response_model=ReceiptUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload receipt",
    description="Upload receipt file for transaction",
)
async def upload_receipt(
    transaction_id: str,
    file: UploadFile = File(..., description="Receipt file (max 10MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload receipt for transaction.

    **Allowed file types:**
    - Images: JPEG, PNG, GIF, WebP
    - Documents: PDF

    **Max file size:** 10MB

    **File validation:**
    - Magic number verification (not just extension)
    - Image corruption check
    - Size limits enforced

    **Security:**
    - Files stored in S3 with encryption
    - Only accessible via presigned URLs
    - Automatic virus scanning (if configured)
    """
    service = ReceiptService(db)
    return await service.upload_receipt(transaction_id, current_user.id, file)


@router.get(
    "/{transaction_id}/receipt",
    response_model=ReceiptResponse,
    summary="Get receipt",
    description="Get receipt with presigned download URL",
)
async def get_receipt(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get receipt with download URL.

    Returns presigned URL valid for 1 hour.
    URL provides secure, time-limited access to file.
    """
    service = ReceiptService(db)
    return await service.get_receipt(transaction_id, current_user.id)


@router.delete(
    "/{transaction_id}/receipt",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete receipt",
    description="Delete receipt file",
)
async def delete_receipt(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete receipt.

    Removes file from S3 and database record.
    """
    service = ReceiptService(db)
    await service.delete_receipt(transaction_id, current_user.id)
    return None


@router.post(
    "/{transaction_id}/receipt/presigned-upload",
    response_model=PresignedUploadUrl,
    summary="Get presigned upload URL",
    description="Get presigned URL for direct client upload",
)
async def get_presigned_upload_url(
    transaction_id: str,
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query(..., description="File content type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get presigned URL for direct client upload.

    **Use case:** Large files that shouldn't go through API server.

    **Flow:**
    1. Client requests presigned URL with filename and content type
    2. Server returns presigned URL and fields
    3. Client uploads directly to S3 using presigned URL
    4. Client calls confirm endpoint with S3 key

    **Benefits:**
    - Faster uploads (no proxy through API)
    - Reduced server load
    - Better for mobile apps

    **URL valid for:** 1 hour
    """
    service = ReceiptService(db)
    return await service.generate_presigned_upload_url(
        transaction_id, current_user.id, filename, content_type
    )


@router.post(
    "/{transaction_id}/receipt/confirm-upload",
    response_model=ReceiptUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm direct upload",
    description="Confirm direct S3 upload and create receipt record",
)
async def confirm_direct_upload(
    transaction_id: str,
    s3_key: str = Form(..., description="S3 object key"),
    filename: str = Form(..., description="Original filename"),
    content_type: str = Form(..., description="File content type"),
    size: int = Form(..., description="File size in bytes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm direct upload to S3.

    Called after client successfully uploads file using presigned URL.
    Creates database record for the uploaded file.
    """
    service = ReceiptService(db)
    return await service.confirm_direct_upload(
        transaction_id, current_user.id, s3_key, filename, content_type, size
    )

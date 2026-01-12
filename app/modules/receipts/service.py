import io
import logging
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.infra.s3 import s3_client
from app.models.receipt import Receipt
from app.modules.receipts.repo import ReceiptRepository
from app.modules.receipts.schemas import (
    PresignedUploadUrl,
    ReceiptResponse,
    ReceiptUploadResponse,
)
from app.modules.transactions.repo import TransactionRepository
from app.utils.file_validation import file_validator

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service for receipt operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReceiptRepository(db)
        self.transaction_repo = TransactionRepository(db)

    async def upload_receipt(
        self, transaction_id: str, user_id: str, file: UploadFile
    ) -> ReceiptUploadResponse:
        """
        Upload receipt for transaction.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for authorization)
            file: Uploaded file

        Returns:
            Receipt upload response

        Raises:
            NotFoundException: If transaction not found
            ConflictException: If receipt already exists
            ValidationException: If file validation fails
        """
        # Verify transaction exists and belongs to user
        transaction = await self.transaction_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundException("Transaction not found")

        # Check if receipt already exists
        existing_receipt = await self.repo.get_by_transaction_id(transaction_id)
        if existing_receipt:
            raise ConflictException(
                "Receipt already exists for this transaction. " "Delete existing receipt first."
            )

        # Read file content
        file_content = await file.read()

        # Validate file
        is_valid, actual_content_type, error = file_validator.validate_file(
            file_content,
            file.filename or "unknown",
            file.content_type or "application/octet-stream",
        )

        if not is_valid:
            raise ValidationException(error or "File validation failed")

        # Generate S3 key
        file_ext = file_validator.get_file_extension(actual_content_type)
        s3_key = f"receipts/{user_id}/{transaction_id}/{uuid4()}{file_ext}"

        # Upload to S3
        file_obj = io.BytesIO(file_content)

        success = await s3_client.upload_file(
            file_obj,
            s3_key,
            actual_content_type,
            metadata={
                "user_id": user_id,
                "transaction_id": transaction_id,
                "original_filename": file_validator.sanitize_filename(file.filename or "unknown"),
            },
        )

        if not success:
            raise ValidationException("Failed to upload file to storage")

        # Create receipt record
        receipt = Receipt(
            transaction_id=transaction_id,
            s3_key=s3_key,
            original_filename=file_validator.sanitize_filename(file.filename or "unknown"),
            content_type=actual_content_type,
            size=len(file_content),
        )

        receipt = await self.repo.create(receipt)
        await self.db.commit()

        logger.info(f"User {user_id} uploaded receipt for transaction {transaction_id}")

        return ReceiptUploadResponse.model_validate(receipt)

    async def get_receipt(self, transaction_id: str, user_id: str) -> ReceiptResponse:
        """
        Get receipt with presigned download URL.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for authorization)

        Returns:
            Receipt with download URL

        Raises:
            NotFoundException: If transaction or receipt not found
        """
        # Verify transaction exists and belongs to user
        transaction = await self.transaction_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundException("Transaction not found")

        # Get receipt
        receipt = await self.repo.get_by_transaction_id(transaction_id)
        if not receipt:
            raise NotFoundException("Receipt not found for this transaction")

        # Generate presigned URL (valid for 1 hour)
        download_url = await s3_client.generate_presigned_url(receipt.s3_key, expiration=3600)

        if not download_url:
            raise ValidationException("Failed to generate download URL")

        return ReceiptResponse(
            id=receipt.id,
            transaction_id=receipt.transaction_id,
            original_filename=receipt.original_filename,
            content_type=receipt.content_type,
            size=receipt.size,
            created_at=receipt.created_at,
            download_url=download_url,
        )

    async def delete_receipt(self, transaction_id: str, user_id: str) -> None:
        """
        Delete receipt.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for authorization)

        Raises:
            NotFoundException: If transaction or receipt not found
        """
        # Verify transaction exists and belongs to user
        transaction = await self.transaction_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundException("Transaction not found")

        # Get receipt
        receipt = await self.repo.get_by_transaction_id(transaction_id)
        if not receipt:
            raise NotFoundException("Receipt not found for this transaction")

        # Delete from S3
        await s3_client.delete_file(receipt.s3_key)

        # Delete from database
        await self.repo.delete(receipt)
        await self.db.commit()

        logger.info(f"User {user_id} deleted receipt for transaction {transaction_id}")

    async def generate_presigned_upload_url(
        self, transaction_id: str, user_id: str, filename: str, content_type: str
    ) -> PresignedUploadUrl:
        """
        Generate presigned URL for direct client upload.
        Useful for large files to avoid proxying through API.

        Args:
            transaction_id: Transaction ID
            user_id: User ID
            filename: Original filename
            content_type: File content type

        Returns:
            Presigned upload URL and fields

        Raises:
            NotFoundException: If transaction not found
            ConflictException: If receipt already exists
            ValidationException: If content type not allowed
        """
        # Verify transaction exists and belongs to user
        transaction = await self.transaction_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundException("Transaction not found")

        # Check if receipt already exists
        existing_receipt = await self.repo.get_by_transaction_id(transaction_id)
        if existing_receipt:
            raise ConflictException("Receipt already exists for this transaction")

        # Validate content type
        if content_type not in file_validator.allowed_mime_types:
            raise ValidationException(f"File type not allowed: {content_type}")

        # Generate S3 key
        file_ext = file_validator.get_file_extension(content_type)
        s3_key = f"receipts/{user_id}/{transaction_id}/{uuid4()}{file_ext}"

        # Generate presigned upload URL
        presigned_data = await s3_client.generate_presigned_upload_url(
            s3_key,
            content_type,
            expiration=3600,  # 1 hour
        )

        if not presigned_data:
            raise ValidationException("Failed to generate upload URL")

        return PresignedUploadUrl(
            upload_url=presigned_data["url"],
            fields=presigned_data["fields"],
            s3_key=s3_key,
            expires_in=3600,
        )

    async def confirm_direct_upload(
        self,
        transaction_id: str,
        user_id: str,
        s3_key: str,
        filename: str,
        content_type: str,
        size: int,
    ) -> ReceiptUploadResponse:
        """
        Confirm direct upload and create receipt record.
        Called after client uploads directly to S3.

        Args:
            transaction_id: Transaction ID
            user_id: User ID
            s3_key: S3 object key
            filename: Original filename
            content_type: File content type
            size: File size in bytes

        Returns:
            Receipt upload response

        Raises:
            NotFoundException: If transaction not found or file not in S3
            ValidationException: If validation fails
        """
        # Verify transaction exists and belongs to user
        transaction = await self.transaction_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundException("Transaction not found")

        # Verify file exists in S3
        exists = await s3_client.file_exists(s3_key)
        if not exists:
            raise NotFoundException("File not found in storage")

        # Verify S3 key matches expected pattern
        expected_prefix = f"receipts/{user_id}/{transaction_id}/"
        if not s3_key.startswith(expected_prefix):
            raise ValidationException("Invalid S3 key")

        # Create receipt record
        receipt = Receipt(
            transaction_id=transaction_id,
            s3_key=s3_key,
            original_filename=file_validator.sanitize_filename(filename),
            content_type=content_type,
            size=size,
        )

        receipt = await self.repo.create(receipt)
        await self.db.commit()

        logger.info(f"User {user_id} confirmed direct upload for transaction {transaction_id}")

        return ReceiptUploadResponse.model_validate(receipt)

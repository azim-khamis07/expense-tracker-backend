"""Unit tests for receipts service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.receipts.schemas import ReceiptResponse, ReceiptUploadResponse
from app.modules.receipts.service import ReceiptService


class TestReceiptService:
    """Test receipts service methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create receipts service instance."""
        return ReceiptService(mock_db)

    @pytest.mark.asyncio
    async def test_upload_receipt_success(self, service, mock_db):
        """Test successful receipt upload."""
        # Mock file
        file_content = b"fake image content"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=file_content)

        # Mock transaction
        mock_transaction = MagicMock()
        mock_transaction.id = "trans123"
        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.get_by_transaction_id = AsyncMock(return_value=None)

        # Mock S3 and file validator
        with (
            patch("app.modules.receipts.service.s3_client") as mock_s3,
            patch("app.modules.receipts.service.file_validator") as mock_validator,
        ):
            mock_s3.upload_file = AsyncMock(return_value=True)
            mock_validator.validate_file = MagicMock(return_value=(True, "image/jpeg", None))
            mock_validator.get_file_extension = MagicMock(return_value=".jpg")
            mock_validator.sanitize_filename = MagicMock(return_value="receipt.jpg")

            # Mock receipt creation
            from datetime import UTC, datetime

            from app.models.receipt import Receipt

            mock_receipt = Receipt(
                id="receipt123",
                transaction_id="trans123",
                s3_key="receipts/user123/trans123/uuid.jpg",
                original_filename="receipt.jpg",
                content_type="image/jpeg",
                size=len(file_content),
                created_at=datetime.now(UTC),
            )
            service.repo.create = AsyncMock(return_value=mock_receipt)
            mock_db.commit = AsyncMock()

            result = await service.upload_receipt("trans123", "user123", mock_file)

            assert isinstance(result, ReceiptUploadResponse)
            assert result.id == "receipt123"
            mock_s3.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_receipt_validation_failure(self, service):
        """Test receipt upload with validation failure."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "receipt.exe"
        mock_file.content_type = "application/x-msdownload"
        mock_file.read = AsyncMock(return_value=b"invalid content")

        mock_transaction = MagicMock()
        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.get_by_transaction_id = AsyncMock(return_value=None)

        with patch("app.modules.receipts.service.file_validator") as mock_validator:
            mock_validator.validate_file = MagicMock(
                return_value=(False, None, "Invalid file type")
            )

            with pytest.raises(ValidationException):
                await service.upload_receipt("trans123", "user123", mock_file)

    @pytest.mark.asyncio
    async def test_get_receipt_success(self, service):
        """Test getting receipt by transaction ID."""
        from app.models.receipt import Receipt
        from app.models.transaction import Transaction

        mock_transaction = Transaction(id="trans123", user_id="user123")
        mock_receipt = Receipt(
            id="receipt123",
            transaction_id="trans123",
            s3_key="receipts/user123/trans123/receipt.jpg",
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            size=1024,
            created_at=datetime.now(UTC),
        )

        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.get_by_transaction_id = AsyncMock(return_value=mock_receipt)

        with patch("app.modules.receipts.service.s3_client") as mock_s3:
            mock_s3.generate_presigned_url = AsyncMock(
                return_value="https://s3.example.com/download"
            )

            result = await service.get_receipt("trans123", "user123")

            assert isinstance(result, ReceiptResponse)
            assert result.id == "receipt123"
            service.repo.get_by_transaction_id.assert_called_once_with("trans123")

    @pytest.mark.asyncio
    async def test_get_receipt_not_found(self, service):
        """Test getting non-existent receipt."""
        from app.models.transaction import Transaction

        mock_transaction = Transaction(id="trans123", user_id="user123")
        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.get_by_transaction_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_receipt("trans123", "user123")

    @pytest.mark.asyncio
    async def test_delete_receipt_success(self, service, mock_db):
        """Test successful receipt deletion."""
        from app.models.receipt import Receipt
        from app.models.transaction import Transaction

        mock_transaction = Transaction(id="trans123", user_id="user123")
        mock_receipt = Receipt(
            id="receipt123",
            transaction_id="trans123",
            s3_key="receipts/user123/trans123/receipt.jpg",
        )
        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.get_by_transaction_id = AsyncMock(return_value=mock_receipt)
        service.repo.delete = AsyncMock()

        with patch("app.modules.receipts.service.s3_client") as mock_s3:
            mock_s3.delete_file = AsyncMock(return_value=True)
            mock_db.commit = AsyncMock()

            await service.delete_receipt("trans123", "user123")

            mock_s3.delete_file.assert_called_once_with("receipts/user123/trans123/receipt.jpg")
            service.repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presigned_upload_url(self, service):
        """Test generating presigned upload URL."""
        from app.models.transaction import Transaction

        mock_transaction = Transaction(id="trans123", user_id="user123")
        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.get_by_transaction_id = AsyncMock(return_value=None)

        with (
            patch("app.modules.receipts.service.s3_client") as mock_s3,
            patch("app.modules.receipts.service.file_validator") as mock_validator,
        ):
            mock_s3.generate_presigned_upload_url = AsyncMock(
                return_value={"url": "https://s3.example.com/upload", "fields": {"key": "value"}}
            )
            mock_validator.allowed_mime_types = ["image/jpeg", "image/png", "application/pdf"]
            mock_validator.get_file_extension = MagicMock(return_value=".jpg")

            result = await service.generate_presigned_upload_url(
                transaction_id="trans123",
                user_id="user123",
                filename="receipt.jpg",
                content_type="image/jpeg",
            )

            assert result is not None
            assert result.upload_url == "https://s3.example.com/upload"
            mock_s3.generate_presigned_upload_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_direct_upload(self, service, mock_db):
        """Test confirming direct upload."""
        from app.models.receipt import Receipt
        from app.models.transaction import Transaction

        mock_transaction = Transaction(id="trans123", user_id="user123")
        mock_receipt = Receipt(
            id="receipt123",
            transaction_id="trans123",
            s3_key="receipts/user123/trans123/receipt.jpg",
            original_filename="receipt.jpg",
            content_type="image/jpeg",
            size=1024,
            created_at=datetime.now(UTC),
        )
        service.transaction_repo.get_by_id = AsyncMock(return_value=mock_transaction)
        service.repo.create = AsyncMock(return_value=mock_receipt)
        mock_db.commit = AsyncMock()

        with (
            patch("app.modules.receipts.service.s3_client") as mock_s3,
            patch("app.modules.receipts.service.file_validator") as mock_validator,
        ):
            mock_s3.file_exists = AsyncMock(return_value=True)
            mock_validator.sanitize_filename = MagicMock(return_value="receipt.jpg")

            result = await service.confirm_direct_upload(
                user_id="user123",
                transaction_id="trans123",
                s3_key="receipts/user123/trans123/receipt.jpg",
                filename="receipt.jpg",
                content_type="image/jpeg",
                size=1024,
            )

            assert isinstance(result, ReceiptUploadResponse)
            service.repo.create.assert_called_once()

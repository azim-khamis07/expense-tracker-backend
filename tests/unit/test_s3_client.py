"""Unit tests for S3 client."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.infra.s3 import S3Client


class TestS3Client:
    """Test S3 client operations."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create mock boto3 S3 client."""
        return MagicMock()

    @pytest.fixture
    @patch("app.infra.s3.boto3")
    @patch("app.infra.s3.settings")
    def s3_client_instance(self, mock_settings, mock_boto3, mock_s3_client):
        """Create S3Client instance with mocked boto3."""
        mock_settings.S3_BUCKET = "test-bucket"
        mock_settings.S3_REGION = "us-east-1"
        mock_settings.S3_ENDPOINT_URL = "http://localhost:9000"
        mock_settings.S3_ACCESS_KEY_ID = "test_key"
        mock_settings.S3_SECRET_ACCESS_KEY = "test_secret"
        mock_settings.AWS_ACCESS_KEY_ID = ""
        mock_settings.AWS_SECRET_ACCESS_KEY = ""

        mock_boto3.client.return_value = mock_s3_client
        return S3Client()

    @pytest.mark.asyncio
    async def test_upload_file_success(self, s3_client_instance, mock_s3_client):
        """Test successful file upload."""
        file_obj = BytesIO(b"test file content")
        mock_s3_client.upload_fileobj.return_value = None

        result = await s3_client_instance.upload_file(file_obj, "test/path/file.txt", "text/plain")

        assert result is True
        mock_s3_client.upload_fileobj.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_with_metadata(self, s3_client_instance, mock_s3_client):
        """Test file upload with metadata."""
        file_obj = BytesIO(b"test content")
        metadata = {"user_id": "123", "transaction_id": "456"}

        result = await s3_client_instance.upload_file(
            file_obj, "test/file.txt", "text/plain", metadata=metadata
        )

        assert result is True
        call_kwargs = mock_s3_client.upload_fileobj.call_args[1]
        assert "Metadata" in call_kwargs["ExtraArgs"]
        assert call_kwargs["ExtraArgs"]["Metadata"] == metadata

    @pytest.mark.asyncio
    async def test_upload_file_error(self, s3_client_instance, mock_s3_client):
        """Test file upload error handling."""
        file_obj = BytesIO(b"test content")
        mock_s3_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )

        result = await s3_client_instance.upload_file(file_obj, "test/file.txt", "text/plain")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_success(self, s3_client_instance, mock_s3_client):
        """Test successful file deletion."""
        mock_s3_client.delete_object.return_value = {}

        result = await s3_client_instance.delete_file("test/path/file.txt")

        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="test/path/file.txt"
        )

    @pytest.mark.asyncio
    async def test_delete_file_error(self, s3_client_instance, mock_s3_client):
        """Test file deletion error handling."""
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "DeleteObject"
        )

        result = await s3_client_instance.delete_file("nonexistent/file.txt")

        assert result is False

    @pytest.mark.asyncio
    async def test_file_exists_true(self, s3_client_instance, mock_s3_client):
        """Test file existence check when file exists."""
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        result = await s3_client_instance.file_exists("test/file.txt")

        assert result is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_file_exists_false(self, s3_client_instance, mock_s3_client):
        """Test file existence check when file doesn't exist."""
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        result = await s3_client_instance.file_exists("nonexistent/file.txt")

        assert result is False

    @pytest.mark.asyncio
    async def test_generate_presigned_url(self, s3_client_instance, mock_s3_client):
        """Test presigned URL generation."""
        mock_s3_client.generate_presigned_url.return_value = "https://presigned-url.com/file"

        result = await s3_client_instance.generate_presigned_url("test/file.txt", expiration=3600)

        assert result == "https://presigned-url.com/file"
        mock_s3_client.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_file_metadata(self, s3_client_instance, mock_s3_client):
        """Test file metadata retrieval."""
        from datetime import datetime

        mock_response = {
            "ContentLength": 1024,
            "ContentType": "image/jpeg",
            "LastModified": datetime(2024, 1, 1),
            "Metadata": {"user_id": "123"},
        }
        mock_s3_client.head_object.return_value = mock_response

        result = await s3_client_instance.get_file_metadata("test/file.jpg")

        assert result is not None
        assert result["size"] == 1024
        assert result["content_type"] == "image/jpeg"
        assert result["metadata"] == {"user_id": "123"}
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test/file.jpg"
        )

    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self, s3_client_instance, mock_s3_client):
        """Test metadata retrieval when file doesn't exist."""
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        result = await s3_client_instance.get_file_metadata("nonexistent/file.txt")

        assert result is None

import logging
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Client:
    """AWS S3 client wrapper for file operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.bucket_name = settings.S3_BUCKET

        # Configure boto3
        config = Config(
            region_name=settings.S3_REGION,
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )

        # Initialize S3 client
        if settings.S3_ENDPOINT_URL:
            # For MinIO or custom S3-compatible storage
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID or settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY
                or settings.AWS_SECRET_ACCESS_KEY,
                config=config,
            )
        else:
            # For AWS S3
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.S3_ACCESS_KEY_ID or settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY
                or settings.AWS_SECRET_ACCESS_KEY,
                config=config,
            )

        logger.info(f"S3 client initialized for bucket: {self.bucket_name}")

    async def upload_file(
        self, file_obj: BinaryIO, object_key: str, content_type: str, metadata: dict | None = None
    ) -> bool:
        """
        Upload file to S3.

        Args:
            file_obj: File object to upload
            object_key: S3 object key (path)
            content_type: MIME type of file
            metadata: Optional metadata dict

        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {"ContentType": content_type}

            # Only use ServerSideEncryption for AWS S3 (not MinIO)
            if not settings.S3_ENDPOINT_URL:
                extra_args["ServerSideEncryption"] = "AES256"  # Encrypt at rest

            if metadata:
                extra_args["Metadata"] = metadata

            # Upload file
            self.s3_client.upload_fileobj(
                file_obj, self.bucket_name, object_key, ExtraArgs=extra_args
            )

            logger.info(f"Uploaded file to S3: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3.

        Args:
            object_key: S3 object key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)

            logger.info(f"Deleted file from S3: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False

    async def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in S3.

        Args:
            object_key: S3 object key to check

        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True

        except ClientError:
            return False

    async def generate_presigned_url(self, object_key: str, expiration: int = 3600) -> str | None:
        """
        Generate presigned URL for file download.

        Args:
            object_key: S3 object key
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration,
            )

            logger.debug(f"Generated presigned URL for: {object_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    async def generate_presigned_upload_url(
        self, object_key: str, content_type: str, expiration: int = 3600
    ) -> dict | None:
        """
        Generate presigned URL for direct file upload (from client).

        Args:
            object_key: S3 object key
            content_type: MIME type of file
            expiration: URL expiration in seconds

        Returns:
            Dict with url and fields, or None if failed
        """
        try:
            response = self.s3_client.generate_presigned_post(
                self.bucket_name,
                object_key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, settings.MAX_UPLOAD_SIZE],
                ],
                ExpiresIn=expiration,
            )

            logger.debug(f"Generated presigned upload URL for: {object_key}")
            return response

        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            return None

    async def get_file_metadata(self, object_key: str) -> dict | None:
        """
        Get file metadata from S3.

        Args:
            object_key: S3 object key

        Returns:
            Metadata dict or None if failed
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)

            return {
                "size": response["ContentLength"],
                "content_type": response["ContentType"],
                "last_modified": response["LastModified"],
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            logger.error(f"Failed to get file metadata: {e}")
            return None


# Global S3 client instance
s3_client = S3Client()


async def get_s3_client() -> S3Client:
    """Dependency for getting S3 client."""
    return s3_client

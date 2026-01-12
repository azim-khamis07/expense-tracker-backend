import io
import logging

import magic
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileValidator:
    """Validator for uploaded files."""

    def __init__(self):
        self.max_size = settings.MAX_UPLOAD_SIZE
        self.allowed_mime_types = settings.ALLOWED_MIME_TYPES_LIST

        # MIME type to extension mapping
        self.mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
        }

    def validate_file(
        self, file_content: bytes, filename: str, declared_content_type: str
    ) -> tuple[bool, str | None, str | None]:
        """
        Validate uploaded file.

        Args:
            file_content: File content as bytes
            filename: Original filename
            declared_content_type: Content-Type from request

        Returns:
            Tuple of (is_valid, actual_content_type, error_message)
        """
        # Check file size
        if len(file_content) > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            return False, None, f"File size exceeds {max_mb}MB limit"

        # Check if file is empty
        if len(file_content) == 0:
            return False, None, "File is empty"

        # Detect actual MIME type using magic numbers
        try:
            mime = magic.Magic(mime=True)
            actual_content_type = mime.from_buffer(file_content)
        except Exception as e:
            logger.error(f"Failed to detect MIME type: {e}")
            return False, None, "Failed to detect file type"

        # Verify MIME type matches allowed types
        if actual_content_type not in self.allowed_mime_types:
            return False, None, f"File type not allowed: {actual_content_type}"

        # Verify declared content type matches actual
        if declared_content_type != actual_content_type:
            logger.warning(
                f"Content type mismatch: declared={declared_content_type}, "
                f"actual={actual_content_type}"
            )
            # Use actual content type

        # Additional validation for images
        if actual_content_type.startswith("image/"):
            is_valid, error = self._validate_image(file_content)
            if not is_valid:
                return False, None, error

        return True, actual_content_type, None

    def _validate_image(self, file_content: bytes) -> tuple[bool, str | None]:
        """
        Validate image file.

        Args:
            file_content: Image content as bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to open image with PIL
            img = Image.open(io.BytesIO(file_content))

            # Verify image (catches corrupted files)
            img.verify()

            # Check image dimensions (optional, reasonable limits)
            img = Image.open(io.BytesIO(file_content))  # Re-open after verify
            width, height = img.size

            if width > 10000 or height > 10000:
                return False, "Image dimensions too large (max 10000x10000)"

            if width < 10 or height < 10:
                return False, "Image dimensions too small (min 10x10)"

            return True, None

        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return False, "Invalid or corrupted image file"

    def get_file_extension(self, content_type: str) -> str:
        """
        Get file extension from content type.

        Args:
            content_type: MIME type

        Returns:
            File extension (e.g., '.jpg')
        """
        return self.mime_to_ext.get(content_type, ".bin")

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing dangerous characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove null bytes
        filename = filename.replace("\x00", "")

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[:250] + ("." + ext if ext else "")

        return filename


# Global validator instance
file_validator = FileValidator()

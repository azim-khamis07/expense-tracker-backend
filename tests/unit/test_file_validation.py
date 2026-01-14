"""Unit tests for file validation."""

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.utils.file_validation import FileValidator


@pytest.mark.unit
class TestFileValidator:
    """Test file validator methods."""

    @pytest.fixture
    def validator(self):
        """Create file validator instance."""
        return FileValidator()

    def test_validate_file_success_image(self, validator):
        """Test successful image file validation."""
        # Create a valid JPEG image
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        file_content = img_bytes.getvalue()

        is_valid, content_type, error = validator.validate_file(
            file_content, "test.jpg", "image/jpeg"
        )

        assert is_valid is True
        assert content_type == "image/jpeg"
        assert error is None

    def test_validate_file_too_large(self, validator):
        """Test validation of file that's too large."""
        # Create large file content
        large_content = b"x" * (validator.max_size + 1)

        is_valid, content_type, error = validator.validate_file(
            large_content, "large.jpg", "image/jpeg"
        )

        assert is_valid is False
        assert error is not None
        assert "exceeds" in error.lower()

    def test_validate_file_empty(self, validator):
        """Test validation of empty file."""
        is_valid, content_type, error = validator.validate_file(b"", "empty.jpg", "image/jpeg")

        assert is_valid is False
        assert error is not None
        assert "empty" in error.lower()

    def test_validate_file_invalid_type(self, validator):
        """Test validation of file with invalid type."""
        is_valid, content_type, error = validator.validate_file(
            b"not an image", "test.exe", "application/x-msdownload"
        )

        assert is_valid is False
        assert error is not None

    @patch("app.utils.file_validation.magic.Magic")
    def test_validate_file_mime_detection_error(self, mock_magic, validator):
        """Test validation when MIME detection fails."""
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_buffer.side_effect = Exception("MIME detection failed")
        mock_magic.return_value = mock_magic_instance

        is_valid, content_type, error = validator.validate_file(
            b"some content", "test.jpg", "image/jpeg"
        )

        assert is_valid is False
        assert error is not None
        assert "detect" in error.lower()

    def test_validate_image_large_dimensions(self, validator):
        """Test image validation with dimensions too large."""
        # Create image with large dimensions
        img = Image.new("RGB", (10001, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        file_content = img_bytes.getvalue()

        is_valid, error = validator._validate_image(file_content)

        assert is_valid is False
        assert error is not None
        assert "large" in error.lower()

    def test_validate_image_small_dimensions(self, validator):
        """Test image validation with dimensions too small."""
        # Create image with small dimensions
        img = Image.new("RGB", (5, 5), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        file_content = img_bytes.getvalue()

        is_valid, error = validator._validate_image(file_content)

        assert is_valid is False
        assert error is not None
        assert "small" in error.lower()

    def test_get_file_extension(self, validator):
        """Test getting file extension from content type."""
        assert validator.get_file_extension("image/jpeg") == ".jpg"
        assert validator.get_file_extension("image/png") == ".png"
        assert validator.get_file_extension("image/gif") == ".gif"
        assert validator.get_file_extension("application/pdf") == ".pdf"
        assert validator.get_file_extension("unknown/type") == ".bin"

    def test_sanitize_filename(self, validator):
        """Test filename sanitization."""
        assert validator.sanitize_filename("test.jpg") == "test.jpg"
        assert validator.sanitize_filename("test/file.jpg") == "test_file.jpg"
        assert validator.sanitize_filename("test\\file.jpg") == "test_file.jpg"
        assert validator.sanitize_filename("test\x00file.jpg") == "testfile.jpg"

        # Test long filename
        long_name = "a" * 300 + ".jpg"
        sanitized = validator.sanitize_filename(long_name)
        assert len(sanitized) <= 255

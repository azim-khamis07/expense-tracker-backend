"""Unit tests for pagination utilities."""

from datetime import UTC, datetime

import pytest

from app.utils.pagination import CursorPage, OffsetPage, decode_cursor, encode_cursor


class TestEncodeDecodeCursor:
    """Test cursor encoding/decoding functions."""

    def test_encode_cursor(self):
        """Test encoding a cursor from timestamp and ID."""
        occurred_at = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        transaction_id = "trans123"

        cursor = encode_cursor(occurred_at, transaction_id)

        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_decode_cursor_valid(self):
        """Test decoding a valid cursor."""
        occurred_at = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        transaction_id = "trans123"

        cursor = encode_cursor(occurred_at, transaction_id)
        decoded_at, decoded_id = decode_cursor(cursor)

        assert decoded_at == occurred_at
        assert decoded_id == transaction_id

    def test_decode_cursor_invalid(self):
        """Test decoding an invalid cursor raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("invalid_cursor")

    def test_decode_cursor_malformed(self):
        """Test decoding a malformed cursor raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not_base64")

    def test_cursor_roundtrip(self):
        """Test cursor encoding and decoding roundtrip."""
        original_at = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        original_id = "trans123"

        cursor = encode_cursor(original_at, original_id)
        decoded_at, decoded_id = decode_cursor(cursor)

        assert decoded_at == original_at
        assert decoded_id == original_id


class TestCursorPage:
    """Test CursorPage model."""

    def test_cursor_page_creation(self):
        """Test creating a CursorPage."""
        page = CursorPage(data=[1, 2, 3], next_cursor="cursor123", has_more=True)

        assert page.data == [1, 2, 3]
        assert page.next_cursor == "cursor123"
        assert page.has_more is True
        assert page.total is None

    def test_cursor_page_with_total(self):
        """Test CursorPage with total count."""
        page = CursorPage(data=[1, 2, 3], total=100)

        assert page.data == [1, 2, 3]
        assert page.total == 100

    def test_cursor_page_last_page(self):
        """Test CursorPage for last page."""
        page = CursorPage(data=[1, 2, 3], next_cursor=None, has_more=False)

        assert page.next_cursor is None
        assert page.has_more is False


class TestOffsetPage:
    """Test OffsetPage model."""

    def test_offset_page_creation(self):
        """Test creating an OffsetPage."""
        page = OffsetPage(data=[1, 2, 3], total=100, page=1, page_size=20, total_pages=5)

        assert page.data == [1, 2, 3]
        assert page.total == 100
        assert page.page == 1
        assert page.page_size == 20
        assert page.total_pages == 5

    def test_offset_page_has_next(self):
        """Test has_next property."""
        page = OffsetPage(data=[1, 2, 3], total=100, page=1, page_size=20, total_pages=5)
        assert page.has_next is True

        page_last = OffsetPage(data=[1, 2, 3], total=100, page=5, page_size=20, total_pages=5)
        assert page_last.has_next is False

    def test_offset_page_has_prev(self):
        """Test has_prev property."""
        page = OffsetPage(data=[1, 2, 3], total=100, page=2, page_size=20, total_pages=5)
        assert page.has_prev is True

        page_first = OffsetPage(data=[1, 2, 3], total=100, page=1, page_size=20, total_pages=5)
        assert page_first.has_prev is False

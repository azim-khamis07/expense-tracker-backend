import base64
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """
    Cursor-based pagination response.

    Attributes:
        data: List of items in current page
        next_cursor: Cursor for next page (None if last page)
        has_more: Whether there are more pages
        total: Optional total count (expensive to compute)
    """

    data: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


def encode_cursor(occurred_at: datetime, id: str) -> str:
    """
    Encode cursor from timestamp and ID.

    Args:
        occurred_at: Transaction timestamp
        id: Transaction ID

    Returns:
        Base64 encoded cursor string
    """
    cursor_str = f"{occurred_at.isoformat()}|{id}"
    return base64.urlsafe_b64encode(cursor_str.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    """
    Decode cursor to timestamp and ID.

    Args:
        cursor: Base64 encoded cursor string

    Returns:
        Tuple of (occurred_at, id)

    Raises:
        ValueError: If cursor is invalid
    """
    try:
        cursor_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        occurred_at_str, id = cursor_str.split("|")
        occurred_at = datetime.fromisoformat(occurred_at_str)
        return occurred_at, id
    except Exception as e:
        raise ValueError(f"Invalid cursor: {e}") from e


class OffsetPage(BaseModel, Generic[T]):
    """
    Offset-based pagination response (simpler but less efficient at scale).

    Attributes:
        data: List of items in current page
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

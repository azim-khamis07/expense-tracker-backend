from datetime import UTC, datetime, timedelta


def utcnow() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(UTC)


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        Timezone-aware UTC datetime
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_date(date_str: str) -> datetime:
    """
    Parse ISO 8601 date string to datetime.

    Args:
        date_str: ISO 8601 formatted date string

    Returns:
        Timezone-aware UTC datetime

    Raises:
        ValueError: If date string is invalid
    """
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return to_utc(dt)
    except Exception as e:
        raise ValueError(f"Invalid date format: {e}") from e


def start_of_month(dt: datetime) -> datetime:
    """Get start of month (00:00:00) for given datetime."""
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def end_of_month(dt: datetime) -> datetime:
    """Get end of month (23:59:59.999999) for given datetime."""
    # Get first day of next month at start of day, then subtract 1 microsecond
    if dt.month == 12:
        next_month = dt.replace(
            year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        next_month = dt.replace(
            month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

    return next_month - timedelta(microseconds=1)


def start_of_day(dt: datetime) -> datetime:
    """Get start of day (00:00:00) for given datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    """Get end of day (23:59:59.999999) for given datetime."""
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def date_range_valid(start_date: datetime, end_date: datetime, max_days: int | None = None) -> bool:
    """
    Validate date range.

    Args:
        start_date: Start of range
        end_date: End of range
        max_days: Optional maximum allowed days in range

    Returns:
        True if valid, False otherwise
    """
    if start_date > end_date:
        return False

    if max_days is not None:
        delta = end_date - start_date
        if delta.days > max_days:
            return False

    return True


def format_month_key(dt: datetime) -> str:
    """
    Format datetime as YYYY-MM for cache keys.

    Args:
        dt: Datetime to format

    Returns:
        String in format "2026-01"
    """
    return dt.strftime("%Y-%m")

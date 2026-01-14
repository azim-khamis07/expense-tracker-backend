"""Unit tests for datetime utilities."""

from datetime import UTC, datetime, timedelta

import pytest

from app.utils.datetime import (
    date_range_valid,
    end_of_day,
    end_of_month,
    format_month_key,
    parse_date,
    start_of_day,
    start_of_month,
    to_utc,
    utcnow,
)


class TestDateTimeUtils:
    """Test datetime utility functions."""

    def test_utcnow(self):
        """Test utcnow returns timezone-aware datetime."""
        result = utcnow()
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC

    def test_to_utc_naive(self):
        """Test converting naive datetime to UTC."""
        naive_dt = datetime(2024, 1, 15, 12, 30, 45)
        result = to_utc(naive_dt)
        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_to_utc_aware(self):
        """Test converting timezone-aware datetime to UTC."""
        # Create datetime with timezone offset
        from datetime import timezone

        aware_dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone(timedelta(hours=5)))
        result = to_utc(aware_dt)
        assert result.tzinfo == UTC
        # Time should be adjusted for timezone
        assert result.hour == 7  # 12 - 5 = 7

    def test_parse_date_iso_format(self):
        """Test parsing ISO 8601 date string."""
        date_str = "2024-01-15T12:30:45Z"
        result = parse_date(date_str)
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_with_timezone(self):
        """Test parsing date string with timezone."""
        date_str = "2024-01-15T12:30:45+05:00"
        result = parse_date(date_str)
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC

    def test_parse_date_invalid(self):
        """Test parsing invalid date string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("invalid-date")

    def test_start_of_month(self):
        """Test getting start of month."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        result = start_of_month(dt)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_end_of_month_regular(self):
        """Test getting end of month for regular month."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        result = end_of_month(dt)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 31
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999

    def test_end_of_month_december(self):
        """Test getting end of month for December."""
        dt = datetime(2024, 12, 15, 12, 30, 45, tzinfo=UTC)
        result = end_of_month(dt)
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 31

    def test_end_of_month_february(self):
        """Test getting end of month for February."""
        dt = datetime(2024, 2, 15, 12, 30, 45, tzinfo=UTC)
        result = end_of_month(dt)
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29  # 2024 is a leap year

    def test_start_of_day(self):
        """Test getting start of day."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        result = start_of_day(dt)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_end_of_day(self):
        """Test getting end of day."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        result = end_of_day(dt)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999

    def test_date_range_valid(self):
        """Test valid date range."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 31, tzinfo=UTC)
        assert date_range_valid(start, end) is True

    def test_date_range_invalid_reversed(self):
        """Test invalid date range (reversed)."""
        start = datetime(2024, 1, 31, tzinfo=UTC)
        end = datetime(2024, 1, 1, tzinfo=UTC)
        assert date_range_valid(start, end) is False

    def test_date_range_valid_with_max_days(self):
        """Test valid date range within max days."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 30, tzinfo=UTC)
        assert date_range_valid(start, end, max_days=30) is True

    def test_date_range_invalid_exceeds_max_days(self):
        """Test invalid date range exceeding max days."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 2, 1, tzinfo=UTC)
        assert date_range_valid(start, end, max_days=30) is False

    def test_date_range_valid_no_max_days(self):
        """Test date range validation without max days."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        assert date_range_valid(start, end) is True

    def test_format_month_key(self):
        """Test formatting datetime as month key."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        result = format_month_key(dt)
        assert result == "2024-01"

    def test_format_month_key_december(self):
        """Test formatting December as month key."""
        dt = datetime(2024, 12, 15, tzinfo=UTC)
        result = format_month_key(dt)
        assert result == "2024-12"

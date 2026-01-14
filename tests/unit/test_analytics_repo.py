"""Unit tests for analytics repository."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.analytics.repo import AnalyticsRepository


class TestAnalyticsRepository:
    """Test analytics repository methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_db):
        """Create analytics repository instance."""
        return AnalyticsRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_category_breakdown(self, repo, mock_db):
        """Test category breakdown query."""
        # Mock result rows
        mock_row1 = MagicMock()
        mock_row1.category_id = "cat1"
        mock_row1.category_name = "Food"
        mock_row1.type = "expense"
        mock_row1.amount = Decimal("100.00")
        mock_row1.transaction_count = 5

        mock_row2 = MagicMock()
        mock_row2.category_id = "cat2"
        mock_row2.category_name = "Salary"
        mock_row2.type = "income"
        mock_row2.amount = Decimal("5000.00")
        mock_row2.transaction_count = 1

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        result = await repo.get_category_breakdown("user123", start_date, end_date)

        assert len(result) == 2
        assert result[0]["category_name"] == "Food"
        assert result[0]["amount"] == Decimal("100.00")
        assert result[1]["category_name"] == "Salary"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_breakdown_with_type_filter(self, repo, mock_db):
        """Test category breakdown with type filter."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        result = await repo.get_category_breakdown(
            "user123", start_date, end_date, transaction_type="expense"
        )

        assert result == []
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_time_series_data_daily(self, repo, mock_db):
        """Test time series data with daily interval."""
        test_date = datetime.now(UTC).date()

        # Mock income query result
        mock_income_row = MagicMock()
        mock_income_row.period = test_date
        mock_income_row.income = Decimal("100.00")

        # Mock expense query result
        mock_expense_row = MagicMock()
        mock_expense_row.period = test_date
        mock_expense_row.expense = Decimal("50.00")

        # Mock count query result
        mock_count_row = MagicMock()
        mock_count_row.period = test_date
        mock_count_row.count = 5

        # Setup execute to return different results for different queries
        call_count = 0

        async def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            # Check query type by examining the select columns
            query_str_lower = str(query).lower()
            if "income" in query_str_lower and call_count == 1:
                mock_result.__iter__ = lambda self: iter([mock_income_row])
            elif "expense" in query_str_lower and call_count == 2:
                mock_result.__iter__ = lambda self: iter([mock_expense_row])
            elif call_count == 3:
                mock_result.__iter__ = lambda self: iter([mock_count_row])
            else:
                mock_result.__iter__ = lambda self: iter([])
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        result = await repo.get_time_series_data("user123", start_date, end_date, "day")

        assert len(result) == 1
        assert result[0]["income"] == Decimal("100.00")
        assert result[0]["expense"] == Decimal("50.00")
        assert result[0]["transaction_count"] == 5
        assert mock_db.execute.call_count == 3  # Three queries: income, expense, count

    @pytest.mark.asyncio
    async def test_get_time_series_data_weekly(self, repo, mock_db):
        """Test time series data with weekly interval."""
        mock_result = MagicMock()
        mock_result.all.return_value = []

        # get_time_series_data executes 3 queries
        mock_db.execute.return_value = mock_result

        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        result = await repo.get_time_series_data("user123", start_date, end_date, "week")

        assert result == []
        assert mock_db.execute.call_count == 3  # Three queries: income, expense, count

    @pytest.mark.asyncio
    async def test_get_time_series_data_monthly(self, repo, mock_db):
        """Test time series data with monthly interval."""
        mock_result = MagicMock()
        mock_result.all.return_value = []

        # get_time_series_data executes 3 queries
        mock_db.execute.return_value = mock_result

        start_date = datetime.now(UTC) - timedelta(days=365)
        end_date = datetime.now(UTC)

        result = await repo.get_time_series_data("user123", start_date, end_date, "month")

        assert result == []
        assert mock_db.execute.call_count == 3  # Three queries: income, expense, count

    @pytest.mark.asyncio
    async def test_get_month_summary(self, repo, mock_db):
        """Test month summary retrieval."""
        # Mock stats query result - returns iterable of rows
        mock_stats_row1 = MagicMock()
        mock_stats_row1.type = "income"
        mock_stats_row1.total = Decimal("5000.00")
        mock_stats_row1.count = 2
        mock_stats_row1.average = Decimal("2500.00")

        mock_stats_row2 = MagicMock()
        mock_stats_row2.type = "expense"
        mock_stats_row2.total = Decimal("2000.00")
        mock_stats_row2.count = 10
        mock_stats_row2.average = Decimal("200.00")

        mock_stats_result = MagicMock()
        mock_stats_result.__iter__ = lambda self: iter([mock_stats_row1, mock_stats_row2])

        # Mock top expense query
        mock_top_expense_result = MagicMock()
        mock_top_expense_row = MagicMock()
        mock_top_expense_row.name = "Food"
        mock_top_expense_row.amount = Decimal("500.00")
        mock_top_expense_result.first.return_value = mock_top_expense_row

        # Mock top income query
        mock_top_income_result = MagicMock()
        mock_top_income_row = MagicMock()
        mock_top_income_row.name = "Salary"
        mock_top_income_row.amount = Decimal("5000.00")
        mock_top_income_result.first.return_value = mock_top_income_row

        # Mock days query
        mock_days_result = MagicMock()
        mock_days_result.scalar_one.return_value = 15

        # Setup execute calls - need to track which query is being executed
        call_count = 0

        async def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            # Stats query (first call) - returns iterable of rows
            if call_count == 1:
                # This is the stats query with GROUP BY Transaction.type
                return mock_stats_result
            # Top expense category query (call 2)
            elif call_count == 2:
                return mock_top_expense_result
            # Top income category query (call 3)
            elif call_count == 3:
                return mock_top_income_result
            # Days query (call 4)
            elif call_count == 4:
                return mock_days_result
            else:
                return mock_stats_result

        mock_db.execute.side_effect = execute_side_effect

        result = await repo.get_month_summary("user123", 2024, 1)

        assert result["month"] == "2024-01"
        assert result["total_income"] == Decimal("5000.00")
        assert result["total_expense"] == Decimal("2000.00")
        assert result["net"] == Decimal("3000.00")
        assert result["transaction_count"] == 12
        assert result["days_with_transactions"] == 15

    @pytest.mark.asyncio
    async def test_get_month_summary_error_handling(self, repo, mock_db):
        """Test month summary error handling."""
        mock_db.execute.side_effect = Exception("Database error")

        result = await repo.get_month_summary("user123", 2024, 1)

        assert result["month"] == "2024-01"
        assert result["total_income"] == Decimal(0)
        assert result["total_expense"] == Decimal(0)
        assert result["transaction_count"] == 0

    @pytest.mark.asyncio
    async def test_get_year_to_date_stats(self, repo, mock_db):
        """Test year-to-date statistics."""
        # Mock stats query result - returns iterable of rows
        mock_income_row = MagicMock()
        mock_income_row.type = "income"
        mock_income_row.total = Decimal("60000.00")

        mock_expense_row = MagicMock()
        mock_expense_row.type = "expense"
        mock_expense_row.total = Decimal("24000.00")

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([mock_income_row, mock_expense_row])
        mock_db.execute.return_value = mock_result

        result = await repo.get_year_to_date_stats("user123", 2024)

        assert result["income"] == Decimal("60000.00")
        assert result["expense"] == Decimal("24000.00")
        assert result["net"] == Decimal("36000.00")
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tag_analytics(self, repo, mock_db):
        """Test tag analytics query."""
        mock_row = MagicMock()
        mock_row.tag_id = "tag1"
        mock_row.tag_name = "Business"
        mock_row.tag_color = "#FF0000"
        mock_row.transaction_count = 20
        mock_row.total_amount = Decimal("5000.00")
        mock_row.average_amount = Decimal("250.00")
        mock_row.expense_count = 15
        mock_row.income_count = 5

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        result = await repo.get_tag_analytics("user123", start_date, end_date)

        assert len(result) == 1
        assert result[0]["tag_name"] == "Business"
        assert result[0]["total_amount"] == Decimal("5000.00")
        assert result[0]["transaction_count"] == 20
        mock_db.execute.assert_called_once()

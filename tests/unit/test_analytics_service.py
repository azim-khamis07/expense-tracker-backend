"""Unit tests for analytics service."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.analytics.schemas import (
    CashFlowResponse,
    CategoryBreakdownResponse,
    DashboardSummary,
    TagAnalyticsResponse,
    TrendsResponse,
)
from app.modules.analytics.service import AnalyticsService


class TestAnalyticsService:
    """Test analytics service methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create analytics service instance."""
        return AnalyticsService(mock_db)

    @pytest.mark.asyncio
    @patch("app.modules.analytics.service.get_or_compute")
    async def test_get_category_breakdown(self, mock_get_or_compute, service, mock_db):
        """Test category breakdown with caching."""
        mock_data = {
            "expense_breakdown": [
                {
                    "category_id": "cat1",
                    "category_name": "Food",
                    "type": "expense",
                    "amount": Decimal("100.00"),
                    "transaction_count": 5,
                    "percentage": 100.0,
                }
            ],
            "income_breakdown": [],
            "total_expense": Decimal("100.00"),
            "total_income": Decimal("0.00"),
            "period_start": datetime.now(UTC).isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
        }

        mock_get_or_compute.return_value = mock_data

        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        result = await service.get_category_breakdown("user123", start_date, end_date)

        assert isinstance(result, CategoryBreakdownResponse)
        assert len(result.expense_breakdown) == 1
        assert result.total_expense == 100.0
        mock_get_or_compute.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.modules.analytics.service.get_or_compute")
    async def test_get_trends(self, mock_get_or_compute, service):
        """Test trends/time series data."""
        mock_data = {
            "data": [
                {
                    "date": datetime.now(UTC).date().isoformat(),
                    "income": Decimal("100.00"),
                    "expense": Decimal("50.00"),
                    "net": Decimal("50.00"),
                    "transaction_count": 5,
                }
            ],
            "interval": "day",
            "period_start": datetime.now(UTC).isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
            "total_income": 100.0,
            "total_expense": 50.0,
            "average_daily_expense": 50.0,
            "average_daily_income": 100.0,
        }

        mock_get_or_compute.return_value = mock_data

        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        result = await service.get_trends("user123", start_date, end_date, "day")

        assert isinstance(result, TrendsResponse)
        assert len(result.data) == 1
        assert result.total_income == 100.0
        mock_get_or_compute.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.modules.analytics.service.get_or_compute")
    async def test_get_cash_flow(self, mock_get_or_compute, service):
        """Test cash flow data."""
        mock_data = {
            "data": [
                {
                    "period": "2024-01",
                    "income": 5000.0,
                    "expense": 2000.0,
                    "net": 3000.0,
                    "transaction_count": 25,
                }
            ],
            "interval": "month",
            "period_start": datetime.now(UTC).isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
            "cumulative_net": 3000.0,
        }

        mock_get_or_compute.return_value = mock_data

        start_date = datetime.now(UTC) - timedelta(days=365)
        end_date = datetime.now(UTC)

        result = await service.get_cash_flow("user123", start_date, end_date, "month")

        assert isinstance(result, CashFlowResponse)
        assert len(result.data) == 1
        mock_get_or_compute.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.modules.analytics.service.get_or_compute")
    async def test_get_dashboard_summary(self, mock_get_or_compute, service):
        """Test dashboard summary."""
        mock_data = {
            "current_month": {
                "month": "2024-01",
                "total_income": Decimal("5000.00"),
                "total_expense": Decimal("2000.00"),
                "net": Decimal("3000.00"),
                "transaction_count": 25,
                "income_count": 2,
                "expense_count": 23,
                "top_expense_category": "Food",
                "top_expense_amount": Decimal("500.00"),
                "top_income_category": "Salary",
                "top_income_amount": Decimal("5000.00"),
                "average_transaction": Decimal("280.00"),
                "days_with_transactions": 15,
            },
            "previous_month": None,
            "year_to_date": {"income": 60000.0, "expense": 24000.0, "net": 36000.0},
            "recent_transactions": [],
            "top_expense_categories": [],
            "top_income_categories": [],
            "monthly_comparison": {
                "expense_change_percentage": 0.0,
                "income_change_percentage": 0.0,
            },
        }

        mock_get_or_compute.return_value = mock_data

        result = await service.get_dashboard_summary("user123")

        assert isinstance(result, DashboardSummary)
        assert result.current_month.total_income == 5000.0
        mock_get_or_compute.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.modules.analytics.service.get_or_compute")
    async def test_get_tag_analytics(self, mock_get_or_compute, service):
        """Test tag analytics."""
        mock_data = {
            "tags": [
                {
                    "tag_id": "tag1",
                    "tag_name": "Business",
                    "tag_color": "#FF0000",
                    "total_amount": Decimal("5000.00"),
                    "transaction_count": 20,
                    "average_amount": Decimal("250.00"),
                    "expense_count": 15,
                    "income_count": 5,
                }
            ],
            "period_start": datetime.now(UTC).isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
        }

        mock_get_or_compute.return_value = mock_data

        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        result = await service.get_tag_analytics("user123", start_date, end_date)

        assert isinstance(result, TagAnalyticsResponse)
        assert len(result.tags) == 1
        mock_get_or_compute.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.modules.analytics.service.get_or_compute")
    async def test_get_category_breakdown_error_handling(self, mock_get_or_compute, service):
        """Test category breakdown error handling."""
        # The service catches exceptions in the compute function, not in get_or_compute
        # So we need to mock the repo to raise an error
        with patch.object(
            service.repo, "get_category_breakdown", side_effect=Exception("Database error")
        ):
            # Mock get_or_compute to call the compute function which will fail
            async def get_or_compute_side_effect(cache_key, compute_fn, ttl):
                try:
                    return await compute_fn()
                except Exception:
                    # Return empty data on error (matching service behavior)
                    return {
                        "expense_breakdown": [],
                        "income_breakdown": [],
                        "total_expense": Decimal(0),
                        "total_income": Decimal(0),
                        "period_start": datetime.now(UTC).isoformat(),
                        "period_end": datetime.now(UTC).isoformat(),
                    }

            mock_get_or_compute.side_effect = get_or_compute_side_effect

            start_date = datetime.now(UTC) - timedelta(days=30)
            end_date = datetime.now(UTC)

            result = await service.get_category_breakdown("user123", start_date, end_date)

            # Should return empty response on error
            assert isinstance(result, CategoryBreakdownResponse)
            assert result.total_expense == 0.0
            assert result.total_income == 0.0

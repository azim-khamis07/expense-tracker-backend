"""Integration tests for analytics endpoints."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User


class TestAnalyticsEndpoints:
    """Test analytics API endpoints."""

    @pytest.mark.asyncio
    async def test_category_breakdown_endpoint(
        self,
        async_client: AsyncClient,
        test_user: User,
        test_categories: list[Category],
        db_session,
        auth_token: str,
    ):
        """Test category breakdown endpoint."""
        # Create some transactions
        from app.modules.transactions.repo import TransactionRepository

        repo = TransactionRepository(db_session)
        transaction = Transaction(
            user_id=test_user.id,
            category_id=test_categories[0].id,
            type="expense",
            amount=100.00,
            currency="USD",
            description="Test expense",
            occurred_at=datetime.now(UTC),
        )
        await repo.create(transaction)
        await db_session.commit()

        # Test endpoint
        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        response = await async_client.get(
            "/api/v1/analytics/category-breakdown",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "expense_breakdown" in data
        assert "income_breakdown" in data
        assert "total_expense" in data
        assert "total_income" in data

    @pytest.mark.asyncio
    async def test_trends_endpoint(
        self, async_client: AsyncClient, test_user: User, auth_token: str
    ):
        """Test trends endpoint."""
        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        response = await async_client.get(
            "/api/v1/analytics/trends",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "interval": "day",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "interval" in data
        assert data["interval"] == "day"

    @pytest.mark.asyncio
    async def test_dashboard_endpoint(
        self, async_client: AsyncClient, test_user: User, auth_token: str
    ):
        """Test dashboard endpoint."""
        response = await async_client.get(
            "/api/v1/analytics/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "current_month" in data
        assert "year_to_date" in data
        assert "recent_transactions" in data

    @pytest.mark.asyncio
    async def test_cash_flow_endpoint(
        self, async_client: AsyncClient, test_user: User, auth_token: str
    ):
        """Test cash flow endpoint."""
        start_date = datetime.now(UTC) - timedelta(days=365)
        end_date = datetime.now(UTC)

        response = await async_client.get(
            "/api/v1/analytics/cashflow",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "interval": "month",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "interval" in data

    @pytest.mark.asyncio
    async def test_tag_analytics_endpoint(
        self, async_client: AsyncClient, test_user: User, auth_token: str
    ):
        """Test tag analytics endpoint."""
        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        response = await async_client.get(
            "/api/v1/analytics/tags",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        # Note: TagAnalyticsResponse doesn't have total_amount, it has tags list
        assert isinstance(data["tags"], list)

    @pytest.mark.asyncio
    async def test_analytics_endpoints_require_auth(self, async_client: AsyncClient):
        """Test that analytics endpoints require authentication."""
        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)

        response = await async_client.get(
            "/api/v1/analytics/category-breakdown",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == 403  # Forbidden without token

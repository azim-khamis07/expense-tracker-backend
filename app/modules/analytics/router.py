from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.analytics.schemas import (
    CashFlowResponse,
    CategoryBreakdownResponse,
    DashboardSummary,
    TagAnalyticsResponse,
    TrendsResponse,
)
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/category-breakdown",
    response_model=CategoryBreakdownResponse,
    summary="Category breakdown",
    description="Get spending/income breakdown by category",
)
async def get_category_breakdown(
    start_date: datetime = Query(..., description="Start date (ISO 8601)"),
    end_date: datetime = Query(..., description="End date (ISO 8601)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get category breakdown with percentages.

    Returns:
    - Expense breakdown by category
    - Income breakdown by category
    - Totals and percentages

    **Cached for 10 minutes.**
    """
    service = AnalyticsService(db)
    return await service.get_category_breakdown(current_user.id, start_date, end_date)


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Trends/time series",
    description="Get time series data (income, expense, net)",
)
async def get_trends(
    start_date: datetime = Query(..., description="Start date (ISO 8601)"),
    end_date: datetime = Query(..., description="End date (ISO 8601)"),
    interval: str = Query(default="day", description="Interval: day, week, or month"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trends/time series data.

    Returns data points with income, expense, and net for each interval.
    Perfect for charts and graphs.

    **Intervals:**
    - `day`: Daily data points
    - `week`: Weekly aggregates
    - `month`: Monthly aggregates

    **Cached for 10 minutes.**
    """
    service = AnalyticsService(db)
    return await service.get_trends(current_user.id, start_date, end_date, interval)


@router.get(
    "/cashflow",
    response_model=CashFlowResponse,
    summary="Cash flow",
    description="Get cash flow data with cumulative net",
)
async def get_cash_flow(
    start_date: datetime = Query(..., description="Start date (ISO 8601)"),
    end_date: datetime = Query(..., description="End date (ISO 8601)"),
    interval: str = Query(default="month", description="Interval: day, week, or month"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cash flow data.

    Shows income, expense, net, and cumulative net over time.
    Perfect for cash flow charts.

    **Cached for 10 minutes.**
    """
    service = AnalyticsService(db)
    return await service.get_cash_flow(current_user.id, start_date, end_date, interval)


@router.get(
    "/dashboard",
    response_model=DashboardSummary,
    summary="Dashboard summary",
    description="Comprehensive dashboard with all key metrics",
)
async def get_dashboard_summary(
    month: str | None = Query(None, description="Month in YYYY-MM format (default: current month)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive dashboard summary.

    **Includes:**
    - Current month summary
    - Previous month summary
    - Year-to-date totals
    - Recent transactions (last 5)
    - Top expense categories (top 5)
    - Top income categories (top 5)
    - Month-over-month comparison

    **Heavily cached (10 minutes) with stampede prevention.**

    This is the main dashboard endpoint - optimized for performance.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(current_user.id, month)


@router.get(
    "/tags",
    response_model=TagAnalyticsResponse,
    summary="Tag analytics",
    description="Get analytics grouped by tags",
)
async def get_tag_analytics(
    start_date: datetime | None = Query(None, description="Start date (ISO 8601)"),
    end_date: datetime | None = Query(None, description="End date (ISO 8601)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics grouped by tags.

    Shows transaction count, total amount, averages, and expense/income breakdown per tag.

    **Cached for 10 minutes.**
    """
    service = AnalyticsService(db)
    return await service.get_tag_analytics(current_user.id, start_date, end_date)

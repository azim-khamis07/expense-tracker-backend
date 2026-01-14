import logging
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

logger = logging.getLogger(__name__)
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
    try:
        service = AnalyticsService(db)
        return await service.get_category_breakdown(current_user.id, start_date, end_date)
    except Exception as e:
        logger.error(
            f"Error in get_category_breakdown for user {current_user.id}: {e}",
            exc_info=True,
        )
        # Return empty response instead of 500 error
        return CategoryBreakdownResponse(
            expense_breakdown=[],
            income_breakdown=[],
            total_expense=0.0,
            total_income=0.0,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
        )


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
    try:
        service = AnalyticsService(db)
        return await service.get_trends(current_user.id, start_date, end_date, interval)
    except Exception as e:
        logger.error(
            f"Error in get_trends for user {current_user.id}: {e}",
            exc_info=True,
        )
        # Return empty response instead of 500 error
        from decimal import Decimal

        return TrendsResponse(
            data=[],
            interval=interval,
            period_start=start_date,
            period_end=end_date,
            total_income=Decimal(0),
            total_expense=Decimal(0),
            average_daily_expense=Decimal(0),
            average_daily_income=Decimal(0),
        )


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
    try:
        service = AnalyticsService(db)
        return await service.get_cash_flow(current_user.id, start_date, end_date, interval)
    except Exception as e:
        logger.error(
            f"Error in get_cash_flow for user {current_user.id}: {e}",
            exc_info=True,
        )
        # Return empty response instead of 500 error
        return CashFlowResponse(
            data_points=[],
            interval=interval,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
        )


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
    try:
        service = AnalyticsService(db)
        return await service.get_dashboard_summary(current_user.id, month)
    except Exception as e:
        logger.error(
            f"Error in get_dashboard_summary for user {current_user.id}: {e}",
            exc_info=True,
        )
        # Return empty dashboard instead of 500 error
        from datetime import UTC

        from app.modules.analytics.schemas import MonthSummary

        current_date = datetime.now(UTC)
        current_month_key = f"{current_date.year}-{current_date.month:02d}"

        return DashboardSummary(
            current_month=MonthSummary(
                month=current_month_key,
                total_income=0.0,
                total_expense=0.0,
                net=0.0,
                transaction_count=0,
                income_count=0,
                expense_count=0,
                top_expense_category=None,
                top_expense_amount=0.0,
                top_income_category=None,
                top_income_amount=0.0,
                average_transaction=0.0,
                days_with_transactions=0,
            ),
            previous_month=None,
            year_to_date={"income": 0.0, "expense": 0.0, "net": 0.0},
            recent_transactions=[],
            top_expense_categories=[],
            top_income_categories=[],
            monthly_comparison={"expense_change_percentage": 0.0, "income_change_percentage": 0.0},
        )


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
    try:
        service = AnalyticsService(db)
        return await service.get_tag_analytics(current_user.id, start_date, end_date)
    except Exception as e:
        logger.error(
            f"Error in get_tag_analytics for user {current_user.id}: {e}",
            exc_info=True,
        )
        # Return empty response instead of 500 error
        return TagAnalyticsResponse(
            tags=[],
            period_start=start_date.isoformat() if start_date else None,
            period_end=end_date.isoformat() if end_date else None,
        )

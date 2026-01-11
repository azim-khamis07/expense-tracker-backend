from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CategoryBreakdown(BaseModel):
    """Category breakdown item."""

    category_id: str | None = None
    category_name: str
    type: str
    amount: Decimal
    transaction_count: int
    percentage: Decimal = Field(description="Percentage of total (for that type)")

    class Config:
        from_attributes = True


class CategoryBreakdownResponse(BaseModel):
    """Category breakdown response."""

    expense_breakdown: list[CategoryBreakdown]
    income_breakdown: list[CategoryBreakdown]
    total_expense: Decimal
    total_income: Decimal
    period_start: datetime
    period_end: datetime


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    income: Decimal
    expense: Decimal
    net: Decimal
    transaction_count: int


class TrendsResponse(BaseModel):
    """Trends/time series response."""

    data: list[TimeSeriesDataPoint]
    interval: str = Field(description="day, week, or month")
    period_start: datetime
    period_end: datetime
    total_income: Decimal
    total_expense: Decimal
    average_daily_expense: Decimal
    average_daily_income: Decimal


class CashFlowItem(BaseModel):
    """Cash flow item."""

    period: str = Field(description="Period label (e.g., '2026-01', 'Week 1')")
    income: Decimal
    expense: Decimal
    net: Decimal
    transaction_count: int


class CashFlowResponse(BaseModel):
    """Cash flow response."""

    data: list[CashFlowItem]
    interval: str
    period_start: datetime
    period_end: datetime
    cumulative_net: Decimal


class MonthSummary(BaseModel):
    """Monthly summary."""

    month: str = Field(description="Month in YYYY-MM format")
    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    transaction_count: int
    income_count: int
    expense_count: int
    top_expense_category: str | None = None
    top_expense_amount: Decimal
    top_income_category: str | None = None
    top_income_amount: Decimal
    average_transaction: Decimal
    days_with_transactions: int


class DashboardSummary(BaseModel):
    """Dashboard summary response."""

    current_month: MonthSummary
    previous_month: MonthSummary | None = None
    year_to_date: dict[str, Decimal] = Field(description="YTD totals (income, expense, net)")
    recent_transactions: list[dict] = Field(description="Last 5 transactions")
    top_expense_categories: list[CategoryBreakdown] = Field(
        description="Top 5 expense categories this month"
    )
    top_income_categories: list[CategoryBreakdown] = Field(
        description="Top 5 income categories this month"
    )
    monthly_comparison: dict[str, Decimal] = Field(
        description="Comparison with previous month (percentage change)"
    )


class TagAnalytics(BaseModel):
    """Tag analytics."""

    tag_id: str
    tag_name: str
    tag_color: str | None = None
    transaction_count: int
    total_amount: Decimal
    average_amount: Decimal
    expense_count: int
    income_count: int


class TagAnalyticsResponse(BaseModel):
    """Tag analytics response."""

    tags: list[TagAnalytics]
    period_start: datetime | None = None
    period_end: datetime | None = None

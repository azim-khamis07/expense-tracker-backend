import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.cache_stampede import get_or_compute
from app.modules.analytics.repo import AnalyticsRepository
from app.modules.analytics.schemas import (
    CashFlowItem,
    CashFlowResponse,
    CategoryBreakdown,
    CategoryBreakdownResponse,
    DashboardSummary,
    MonthSummary,
    TagAnalytics,
    TagAnalyticsResponse,
    TimeSeriesDataPoint,
    TrendsResponse,
)
from app.modules.transactions.repo import TransactionRepository
from app.utils.datetime_utils import end_of_month, format_month_key, start_of_month

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics with caching."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalyticsRepository(db)
        self.transaction_repo = TransactionRepository(db)

    async def get_category_breakdown(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> CategoryBreakdownResponse:
        """
        Get category breakdown with percentages.
        Cached for 10 minutes.
        """
        cache_key = f"analytics:breakdown:{user_id}:{start_date.date()}:{end_date.date()}"

        async def compute():
            # Get breakdown data
            breakdown = await self.repo.get_category_breakdown(user_id, start_date, end_date)

            # Separate by type and calculate percentages
            expense_items = [b for b in breakdown if b["type"] == "expense"]
            income_items = [b for b in breakdown if b["type"] == "income"]

            total_expense = sum(b["amount"] for b in expense_items)
            total_income = sum(b["amount"] for b in income_items)

            # Calculate percentages
            expense_breakdown = []
            for item in expense_items:
                percentage = (
                    (item["amount"] / total_expense * 100) if total_expense > 0 else Decimal(0)
                )
                expense_breakdown.append(
                    CategoryBreakdown(**item, percentage=percentage).model_dump()
                )

            income_breakdown = []
            for item in income_items:
                percentage = (
                    (item["amount"] / total_income * 100) if total_income > 0 else Decimal(0)
                )
                income_breakdown.append(
                    CategoryBreakdown(**item, percentage=percentage).model_dump()
                )

            return {
                "expense_breakdown": expense_breakdown,
                "income_breakdown": income_breakdown,
                "total_expense": float(total_expense),
                "total_income": float(total_income),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
            }

        # Get from cache or compute
        data = await get_or_compute(cache_key, compute, ttl=600)

        # Convert back to Pydantic models
        return CategoryBreakdownResponse(
            expense_breakdown=[CategoryBreakdown(**b) for b in data["expense_breakdown"]],
            income_breakdown=[CategoryBreakdown(**b) for b in data["income_breakdown"]],
            total_expense=Decimal(str(data["total_expense"])),
            total_income=Decimal(str(data["total_income"])),
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
        )

    async def get_trends(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "day",
    ) -> TrendsResponse:
        """
        Get trends/time series data.
        Cached for 10 minutes.
        """
        cache_key = f"analytics:trends:{user_id}:{start_date.date()}:{end_date.date()}:{interval}"

        async def compute():
            # Get time series data
            data = await self.repo.get_time_series_data(user_id, start_date, end_date, interval)

            # Calculate totals
            total_income = sum(d["income"] for d in data)
            total_expense = sum(d["expense"] for d in data)

            # Calculate averages
            days_count = (end_date - start_date).days + 1
            avg_daily_expense = total_expense / days_count if days_count > 0 else Decimal(0)
            avg_daily_income = total_income / days_count if days_count > 0 else Decimal(0)

            return {
                "data": data,
                "interval": interval,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_income": float(total_income),
                "total_expense": float(total_expense),
                "average_daily_expense": float(avg_daily_expense),
                "average_daily_income": float(avg_daily_income),
            }

        # Get from cache or compute
        cached_data = await get_or_compute(cache_key, compute, ttl=600)

        # Convert to Pydantic models
        data_points = [TimeSeriesDataPoint(**d) for d in cached_data["data"]]

        return TrendsResponse(
            data=data_points,
            interval=cached_data["interval"],
            period_start=datetime.fromisoformat(cached_data["period_start"]),
            period_end=datetime.fromisoformat(cached_data["period_end"]),
            total_income=Decimal(str(cached_data["total_income"])),
            total_expense=Decimal(str(cached_data["total_expense"])),
            average_daily_expense=Decimal(str(cached_data["average_daily_expense"])),
            average_daily_income=Decimal(str(cached_data["average_daily_income"])),
        )

    async def get_cash_flow(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "month",
    ) -> CashFlowResponse:
        """
        Get cash flow data.
        Cached for 10 minutes.
        """
        cache_key = f"analytics:cashflow:{user_id}:{start_date.date()}:{end_date.date()}:{interval}"

        async def compute():
            # Get time series data
            data = await self.repo.get_time_series_data(user_id, start_date, end_date, interval)

            # Calculate cumulative net
            cumulative_net = Decimal(0)
            cash_flow_items = []

            for item in data:
                cumulative_net += item["net"]
                cash_flow_items.append(
                    {
                        "period": item["date"],
                        "income": float(item["income"]),
                        "expense": float(item["expense"]),
                        "net": float(item["net"]),
                        "transaction_count": item["transaction_count"],
                    }
                )

            return {
                "data": cash_flow_items,
                "interval": interval,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "cumulative_net": float(cumulative_net),
            }

        # Get from cache or compute
        cached_data = await get_or_compute(cache_key, compute, ttl=600)

        # Convert to Pydantic models
        items = [CashFlowItem(**d) for d in cached_data["data"]]

        return CashFlowResponse(
            data=items,
            interval=cached_data["interval"],
            period_start=datetime.fromisoformat(cached_data["period_start"]),
            period_end=datetime.fromisoformat(cached_data["period_end"]),
            cumulative_net=Decimal(str(cached_data["cumulative_net"])),
        )

    async def get_dashboard_summary(
        self,
        user_id: str,
        month: str | None = None,
    ) -> DashboardSummary:
        """
        Get comprehensive dashboard summary.
        Heavily cached (10 minutes).

        Args:
            month: Optional month in YYYY-MM format (default: current month)
        """
        # Parse or use current month
        if month:
            year, month_num = map(int, month.split("-"))
            current_date = datetime(year, month_num, 1, tzinfo=UTC)
        else:
            current_date = datetime.now(UTC)
            year = current_date.year
            month_num = current_date.month

        cache_key = f"dash:{user_id}:{format_month_key(current_date)}:summary"

        async def compute():
            # Get current month summary
            current_month = await self.repo.get_month_summary(user_id, year, month_num)

            # Get previous month summary
            prev_date = current_date - timedelta(days=1)
            prev_month = await self.repo.get_month_summary(user_id, prev_date.year, prev_date.month)

            # Get year-to-date stats
            ytd_stats = await self.repo.get_year_to_date_stats(user_id, year)

            # Get recent transactions (last 5)
            start = start_of_month(current_date)
            end = end_of_month(current_date)

            transactions, _, _ = await self.transaction_repo.list_with_filters(
                user_id=user_id, start_date=start, end_date=end, limit=5
            )

            recent_transactions = []
            for t in transactions:
                recent_transactions.append(
                    {
                        "id": t.id,
                        "amount": float(t.amount),
                        "type": t.type,
                        "description": t.description,
                        "occurred_at": t.occurred_at.isoformat(),
                    }
                )

            # Get top categories for current month
            breakdown = await self.repo.get_category_breakdown(user_id, start, end)

            expense_categories = [b for b in breakdown if b["type"] == "expense"][:5]
            income_categories = [b for b in breakdown if b["type"] == "income"][:5]

            total_expense = sum(b["amount"] for b in expense_categories)
            total_income = sum(b["amount"] for b in income_categories)

            top_expense_cats = []
            for cat in expense_categories:
                percentage = (
                    (cat["amount"] / total_expense * 100) if total_expense > 0 else Decimal(0)
                )
                top_expense_cats.append(
                    {
                        "category_id": cat["category_id"],
                        "category_name": cat["category_name"],
                        "type": cat["type"],
                        "amount": float(cat["amount"]),
                        "transaction_count": cat["transaction_count"],
                        "percentage": float(percentage),
                    }
                )

            top_income_cats = []
            for cat in income_categories:
                percentage = (
                    (cat["amount"] / total_income * 100) if total_income > 0 else Decimal(0)
                )
                top_income_cats.append(
                    {
                        "category_id": cat["category_id"],
                        "category_name": cat["category_name"],
                        "type": cat["type"],
                        "amount": float(cat["amount"]),
                        "transaction_count": cat["transaction_count"],
                        "percentage": float(percentage),
                    }
                )

            # Calculate month-over-month comparison
            current_expense = current_month["total_expense"]
            prev_expense = prev_month["total_expense"]
            expense_change = (
                ((current_expense - prev_expense) / prev_expense * 100)
                if prev_expense > 0
                else Decimal(0)
            )

            current_income = current_month["total_income"]
            prev_income = prev_month["total_income"]
            income_change = (
                ((current_income - prev_income) / prev_income * 100)
                if prev_income > 0
                else Decimal(0)
            )

            return {
                "current_month": current_month,
                "previous_month": prev_month,
                "year_to_date": {
                    "income": float(ytd_stats["income"]),
                    "expense": float(ytd_stats["expense"]),
                    "net": float(ytd_stats["net"]),
                },
                "recent_transactions": recent_transactions,
                "top_expense_categories": top_expense_cats,
                "top_income_categories": top_income_cats,
                "monthly_comparison": {
                    "expense_change_percentage": float(expense_change),
                    "income_change_percentage": float(income_change),
                },
            }

        # Get from cache or compute with stampede prevention
        cached_data = await get_or_compute(cache_key, compute, ttl=600)

        # Convert to Pydantic models
        return DashboardSummary(
            current_month=MonthSummary(**cached_data["current_month"]),
            previous_month=(
                MonthSummary(**cached_data["previous_month"])
                if cached_data["previous_month"]
                else None
            ),
            year_to_date=cached_data["year_to_date"],
            recent_transactions=cached_data["recent_transactions"],
            top_expense_categories=[
                CategoryBreakdown(**c) for c in cached_data["top_expense_categories"]
            ],
            top_income_categories=[
                CategoryBreakdown(**c) for c in cached_data["top_income_categories"]
            ],
            monthly_comparison=cached_data["monthly_comparison"],
        )

    async def get_tag_analytics(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TagAnalyticsResponse:
        """
        Get tag analytics.
        Cached for 10 minutes.
        """
        start_str = start_date.date().isoformat() if start_date else "all"
        end_str = end_date.date().isoformat() if end_date else "all"
        cache_key = f"analytics:tags:{user_id}:{start_str}:{end_str}"

        async def compute():
            analytics = await self.repo.get_tag_analytics(user_id, start_date, end_date)

            return {
                "tags": analytics,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None,
            }

        # Get from cache or compute
        cached_data = await get_or_compute(cache_key, compute, ttl=600)

        # Convert to Pydantic models
        tags = [TagAnalytics(**t) for t in cached_data["tags"]]

        return TagAnalyticsResponse(
            tags=tags,
            period_start=(
                datetime.fromisoformat(cached_data["period_start"])
                if cached_data["period_start"]
                else None
            ),
            period_end=(
                datetime.fromisoformat(cached_data["period_end"])
                if cached_data["period_end"]
                else None
            ),
        )

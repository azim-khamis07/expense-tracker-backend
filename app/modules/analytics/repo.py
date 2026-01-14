import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.tag import Tag, transaction_tags
from app.models.transaction import Transaction
from app.utils.datetime import end_of_month

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Repository for analytics queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_category_breakdown(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        transaction_type: str | None = None,
    ) -> list[dict]:
        """
        Get spending/income breakdown by category.

        Returns list of dicts with:
        - category_id, category_name, type, amount, transaction_count
        """
        # Build query
        query = (
            select(
                Transaction.category_id,
                Category.name.label("category_name"),
                Transaction.type,
                func.sum(Transaction.amount).label("amount"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.occurred_at >= start_date,
                    Transaction.occurred_at <= end_date,
                )
            )
        )

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        query = query.group_by(Transaction.category_id, Category.name, Transaction.type).order_by(
            func.sum(Transaction.amount).desc()
        )

        result = await self.db.execute(query)
        rows = result.all()

        breakdown = []
        for row in rows:
            breakdown.append(
                {
                    "category_id": row.category_id,
                    "category_name": row.category_name or "Uncategorized",
                    "type": row.type,
                    "amount": Decimal(str(row.amount)),
                    "transaction_count": row.transaction_count,
                }
            )

        return breakdown

    async def get_time_series_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "day",
    ) -> list[dict]:
        """
        Get time series data (income, expense, net by interval).

        Args:
            interval: 'day', 'week', or 'month'
        """
        if interval == "day":
            date_trunc = func.date(Transaction.occurred_at)
        elif interval == "week":
            # PostgreSQL: date_trunc('week', occurred_at)
            date_trunc = func.date_trunc("week", Transaction.occurred_at)
        else:  # month
            date_trunc = func.date_trunc("month", Transaction.occurred_at)

        # Query for income
        income_period = date_trunc.label("period")
        income_query = (
            select(
                income_period,
                func.coalesce(func.sum(Transaction.amount), 0).label("income"),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.type == "income",
                    Transaction.occurred_at >= start_date,
                    Transaction.occurred_at <= end_date,
                )
            )
            .group_by(income_period)
        )

        # Query for expense
        expense_period = date_trunc.label("period")
        expense_query = (
            select(
                expense_period,
                func.coalesce(func.sum(Transaction.amount), 0).label("expense"),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.type == "expense",
                    Transaction.occurred_at >= start_date,
                    Transaction.occurred_at <= end_date,
                )
            )
            .group_by(expense_period)
        )

        # Query for transaction count
        count_period = date_trunc.label("period")
        count_query = (
            select(
                count_period,
                func.count(Transaction.id).label("count"),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.occurred_at >= start_date,
                    Transaction.occurred_at <= end_date,
                )
            )
            .group_by(count_period)
        )

        # Execute queries
        income_result = await self.db.execute(income_query)
        expense_result = await self.db.execute(expense_query)
        count_result = await self.db.execute(count_query)

        # Aggregate results
        income_data = {row.period: Decimal(str(row.income)) for row in income_result}
        expense_data = {row.period: Decimal(str(row.expense)) for row in expense_result}
        count_data = {row.period: row.count for row in count_result}

        # Get all unique periods
        all_periods = set(income_data.keys()) | set(expense_data.keys()) | set(count_data.keys())

        # Build result
        result = []
        for period in sorted(all_periods):
            income = income_data.get(period, Decimal(0))
            expense = expense_data.get(period, Decimal(0))

            result.append(
                {
                    "date": (
                        period.strftime("%Y-%m-%d") if hasattr(period, "strftime") else str(period)
                    ),
                    "income": income,
                    "expense": expense,
                    "net": income - expense,
                    "transaction_count": count_data.get(period, 0),
                }
            )

        return result

    async def get_month_summary(
        self,
        user_id: str,
        year: int,
        month: int,
    ) -> dict:
        """Get comprehensive summary for a specific month."""
        try:
            start = datetime(year, month, 1, tzinfo=UTC)
            end = end_of_month(start)

            # Get basic stats
            stats_query = (
                select(
                    Transaction.type,
                    func.sum(Transaction.amount).label("total"),
                    func.count(Transaction.id).label("count"),
                    func.avg(Transaction.amount).label("average"),
                )
                .where(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.deleted_at.is_(None),
                        Transaction.occurred_at >= start,
                        Transaction.occurred_at <= end,
                    )
                )
                .group_by(Transaction.type)
            )

            result = await self.db.execute(stats_query)
            stats = {row.type: row for row in result}

            income_stats = stats.get("income")
            expense_stats = stats.get("expense")

            total_income = Decimal(str(income_stats.total)) if income_stats else Decimal(0)
            total_expense = Decimal(str(expense_stats.total)) if expense_stats else Decimal(0)
            income_count = income_stats.count if income_stats else 0
            expense_count = expense_stats.count if expense_stats else 0

            # Get top expense category
            top_expense = await self.db.execute(
                select(Category.name, func.sum(Transaction.amount).label("amount"))
                .join(Category, Category.id == Transaction.category_id)
                .where(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.deleted_at.is_(None),
                        Transaction.type == "expense",
                        Transaction.occurred_at >= start,
                        Transaction.occurred_at <= end,
                    )
                )
                .group_by(Category.name)
                .order_by(func.sum(Transaction.amount).desc())
                .limit(1)
            )
            top_expense_row = top_expense.first()

            # Get top income category
            top_income = await self.db.execute(
                select(Category.name, func.sum(Transaction.amount).label("amount"))
                .join(Category, Category.id == Transaction.category_id)
                .where(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.deleted_at.is_(None),
                        Transaction.type == "income",
                        Transaction.occurred_at >= start,
                        Transaction.occurred_at <= end,
                    )
                )
                .group_by(Category.name)
                .order_by(func.sum(Transaction.amount).desc())
                .limit(1)
            )
            top_income_row = top_income.first()

            # Get days with transactions
            days_query = select(func.count(distinct(func.date(Transaction.occurred_at)))).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.occurred_at >= start,
                    Transaction.occurred_at <= end,
                )
            )
            days_result = await self.db.execute(days_query)
            days_with_transactions = days_result.scalar_one() or 0

            total_count = income_count + expense_count

            return {
                "month": f"{year}-{month:02d}",
                "total_income": total_income,
                "total_expense": total_expense,
                "net": total_income - total_expense,
                "transaction_count": total_count,
                "income_count": income_count,
                "expense_count": expense_count,
                "top_expense_category": top_expense_row.name if top_expense_row else None,
                "top_expense_amount": (
                    Decimal(str(top_expense_row.amount)) if top_expense_row else Decimal(0)
                ),
                "top_income_category": top_income_row.name if top_income_row else None,
                "top_income_amount": (
                    Decimal(str(top_income_row.amount)) if top_income_row else Decimal(0)
                ),
                "average_transaction": (
                    (total_income + total_expense) / total_count if total_count > 0 else Decimal(0)
                ),
                "days_with_transactions": days_with_transactions,
            }
        except Exception as e:
            logger.error(
                f"Error getting month summary for user {user_id}, {year}-{month:02d}: {e}",
                exc_info=True,
            )
            # Return empty/default summary instead of raising
            return {
                "month": f"{year}-{month:02d}",
                "total_income": Decimal(0),
                "total_expense": Decimal(0),
                "net": Decimal(0),
                "transaction_count": 0,
                "income_count": 0,
                "expense_count": 0,
                "top_expense_category": None,
                "top_expense_amount": Decimal(0),
                "top_income_category": None,
                "top_income_amount": Decimal(0),
                "average_transaction": Decimal(0),
                "days_with_transactions": 0,
            }

    async def get_year_to_date_stats(
        self,
        user_id: str,
        year: int,
    ) -> dict:
        """Get year-to-date statistics."""
        start = datetime(year, 1, 1, tzinfo=UTC)
        end = datetime.now(UTC)

        stats_query = (
            select(
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.occurred_at >= start,
                    Transaction.occurred_at <= end,
                )
            )
            .group_by(Transaction.type)
        )

        result = await self.db.execute(stats_query)
        stats = {row.type: Decimal(str(row.total)) for row in result}

        income = stats.get("income", Decimal(0))
        expense = stats.get("expense", Decimal(0))

        return {
            "income": income,
            "expense": expense,
            "net": income - expense,
        }

    async def get_tag_analytics(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """Get analytics grouped by tags."""
        # Build conditions
        conditions = [
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        ]

        if start_date:
            conditions.append(Transaction.occurred_at >= start_date)

        if end_date:
            conditions.append(Transaction.occurred_at <= end_date)

        # Query
        query = (
            select(
                Tag.id.label("tag_id"),
                Tag.name.label("tag_name"),
                Tag.color.label("tag_color"),
                func.count(Transaction.id).label("transaction_count"),
                func.sum(Transaction.amount).label("total_amount"),
                func.avg(Transaction.amount).label("average_amount"),
                func.sum(case((Transaction.type == "expense", 1), else_=0)).label("expense_count"),
                func.sum(case((Transaction.type == "income", 1), else_=0)).label("income_count"),
            )
            .join(transaction_tags, transaction_tags.c.tag_id == Tag.id)
            .join(Transaction, Transaction.id == transaction_tags.c.transaction_id)
            .where(and_(*conditions))
            .group_by(Tag.id, Tag.name, Tag.color)
            .order_by(func.count(Transaction.id).desc())
        )

        result = await self.db.execute(query)
        rows = result.all()

        analytics = []
        for row in rows:
            analytics.append(
                {
                    "tag_id": row.tag_id,
                    "tag_name": row.tag_name,
                    "tag_color": row.tag_color,
                    "transaction_count": row.transaction_count,
                    "total_amount": Decimal(str(row.total_amount)),
                    "average_amount": Decimal(str(row.average_amount)),
                    "expense_count": row.expense_count,
                    "income_count": row.income_count,
                }
            )

        return analytics

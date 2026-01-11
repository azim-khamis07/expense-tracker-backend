import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, delete, desc, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.tag import Tag, transaction_tags
from app.models.transaction import Transaction
from app.utils.pagination import decode_cursor, encode_cursor

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for transaction database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        transaction_id: str,
        user_id: str,
        include_deleted: bool = False,
    ) -> Transaction | None:
        """Get transaction by ID."""
        query = (
            select(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.tags),
                joinedload(Transaction.receipt),
            )
            .where(and_(Transaction.id == transaction_id, Transaction.user_id == user_id))
        )

        if not include_deleted:
            query = query.where(Transaction.deleted_at.is_(None))

        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def list_with_filters(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category_id: str | None = None,
        type: str | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        tag_ids: list[str] | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Transaction], str | None, bool]:
        """
        List transactions with filters and cursor pagination.

        Returns:
            Tuple of (transactions, next_cursor, has_more)
        """
        # Build base query
        query = (
            select(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.tags),
                joinedload(Transaction.receipt),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.deleted_at.is_(None),
                )
            )
        )

        # Apply filters
        if start_date:
            query = query.where(Transaction.occurred_at >= start_date)

        if end_date:
            query = query.where(Transaction.occurred_at <= end_date)

        if category_id:
            query = query.where(Transaction.category_id == category_id)

        if type:
            query = query.where(Transaction.type == type)

        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)

        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)

        # Filter by tags (transactions with ANY of the specified tags)
        if tag_ids:
            query = (
                query.join(transaction_tags)
                .where(transaction_tags.c.tag_id.in_(tag_ids))
                .distinct()
            )

        # Apply cursor pagination
        if cursor:
            try:
                cursor_occurred_at, cursor_id = decode_cursor(cursor)
                query = query.where(
                    or_(
                        Transaction.occurred_at < cursor_occurred_at,
                        and_(
                            Transaction.occurred_at == cursor_occurred_at,
                            Transaction.id < cursor_id,
                        ),
                    )
                )
            except ValueError:
                logger.warning(f"Invalid cursor: {cursor}")

        # Order by occurred_at DESC, id DESC (newest first)
        query = query.order_by(desc(Transaction.occurred_at), desc(Transaction.id))

        # Fetch limit + 1 to check if there are more
        query = query.limit(limit + 1)

        result = await self.db.execute(query)
        transactions = list(result.unique().scalars().all())

        # Check if there are more results
        has_more = len(transactions) > limit
        if has_more:
            transactions = transactions[:limit]

        # Generate next cursor
        next_cursor = None
        if has_more and transactions:
            last_transaction = transactions[-1]
            next_cursor = encode_cursor(last_transaction.occurred_at, last_transaction.id)

        return transactions, next_cursor, has_more

    async def create(self, transaction: Transaction) -> Transaction:
        """Create new transaction."""
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        logger.info(f"Created transaction: {transaction.id}")
        return transaction

    async def update(self, transaction: Transaction) -> Transaction:
        """Update existing transaction."""
        await self.db.flush()
        await self.db.refresh(transaction)
        logger.info(f"Updated transaction: {transaction.id}")
        return transaction

    async def soft_delete(self, transaction: Transaction) -> Transaction:
        """Soft delete transaction."""
        transaction.deleted_at = datetime.now(UTC)
        return await self.update(transaction)

    async def get_stats(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category_id: str | None = None,
    ) -> dict[str, Decimal | int]:
        """Get transaction statistics."""
        # Build base query
        conditions = [
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        ]

        if start_date:
            conditions.append(Transaction.occurred_at >= start_date)

        if end_date:
            conditions.append(Transaction.occurred_at <= end_date)

        if category_id:
            conditions.append(Transaction.category_id == category_id)

        # Get income stats
        income_query = select(
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("count"),
        ).where(and_(*conditions, Transaction.type == "income"))

        income_result = await self.db.execute(income_query)
        income_row = income_result.one()

        # Get expense stats
        expense_query = select(
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("count"),
        ).where(and_(*conditions, Transaction.type == "expense"))

        expense_result = await self.db.execute(expense_query)
        expense_row = expense_result.one()

        total_count = income_row.count + expense_row.count
        total_income = Decimal(str(income_row.total))
        total_expense = Decimal(str(expense_row.total))

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net": total_income - total_expense,
            "transaction_count": total_count,
            "average_transaction": (
                (total_income + total_expense) / total_count if total_count > 0 else Decimal(0)
            ),
        }

    async def attach_tags(self, transaction: Transaction, tag_ids: list[str]) -> None:
        """Attach tags to transaction."""
        # Validate tags belong to user
        result = await self.db.execute(
            select(Tag).where(and_(Tag.id.in_(tag_ids), Tag.user_id == transaction.user_id))
        )
        valid_tags = list(result.scalars().all())

        if len(valid_tags) != len(tag_ids):
            raise ValueError("Some tags not found or don't belong to user")

        # Delete existing tags from junction table
        await self.db.execute(
            delete(transaction_tags).where(transaction_tags.c.transaction_id == transaction.id)
        )

        # Insert new tags into junction table
        if valid_tags:
            await self.db.execute(
                insert(transaction_tags).values(
                    [{"transaction_id": transaction.id, "tag_id": tag.id} for tag in valid_tags]
                )
            )

        await self.db.flush()

    async def clear_tags(self, transaction: Transaction) -> None:
        """Remove all tags from transaction."""
        transaction.tags = []
        await self.db.flush()

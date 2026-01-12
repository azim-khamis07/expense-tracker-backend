import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException, ValidationException
from app.infra.redis import invalidate_cache_pattern
from app.models.transaction import Transaction
from app.modules.categories.repo import CategoryRepository
from app.modules.transactions.repo import TransactionRepository
from app.modules.transactions.schemas import (
    TransactionCreate,
    TransactionListFilter,
    TransactionPage,
    TransactionResponse,
    TransactionStats,
    TransactionUpdate,
)
from app.utils.datetime_utils import format_month_key, to_utc

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for transaction business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransactionRepository(db)
        self.category_repo = CategoryRepository(db)

    async def create_transaction(
        self, user_id: str, data: TransactionCreate
    ) -> TransactionResponse:
        """Create new transaction."""
        # Validate category belongs to user (if provided)
        if data.category_id:
            category = await self.category_repo.get_by_id(data.category_id, user_id)
            if not category:
                raise ValidationException("Category not found")

        # Normalize occurred_at to UTC
        occurred_at = to_utc(data.occurred_at)

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            category_id=data.category_id,
            amount=data.amount,
            currency=data.currency,
            type=data.type,
            description=data.description,
            note=data.note,
            occurred_at=occurred_at,
        )

        transaction = await self.repo.create(transaction)

        # Attach tags
        if data.tag_ids:
            await self.repo.attach_tags(transaction, data.tag_ids)

        await self.db.commit()

        # Refresh transaction with relationships loaded for response serialization
        result = await self.db.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.tags),
                joinedload(Transaction.receipt),
            )
            .where(Transaction.id == transaction.id)
        )
        transaction = result.unique().scalar_one()

        # Invalidate cache
        await self._invalidate_cache(user_id, occurred_at)

        logger.info(
            f"User {user_id} created {data.type} transaction: " f"{data.amount} {data.currency}"
        )

        return await self._to_response(transaction)

    async def get_transaction(self, transaction_id: str, user_id: str) -> TransactionResponse:
        """Get transaction by ID."""
        transaction = await self.repo.get_by_id(transaction_id, user_id)

        if not transaction:
            raise NotFoundException("Transaction not found")

        return await self._to_response(transaction)

    async def list_transactions(
        self, user_id: str, filters: TransactionListFilter
    ) -> TransactionPage:
        """List transactions with filters and pagination."""
        # Normalize dates to UTC
        start_date = to_utc(filters.start_date) if filters.start_date else None
        end_date = to_utc(filters.end_date) if filters.end_date else None

        # Validate category belongs to user (if provided)
        if filters.category_id:
            category = await self.category_repo.get_by_id(filters.category_id, user_id)
            if not category:
                raise ValidationException("Category not found")

        # Get transactions
        transactions, next_cursor, has_more = await self.repo.list_with_filters(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            category_id=filters.category_id,
            type=filters.type,
            min_amount=filters.min_amount,
            max_amount=filters.max_amount,
            tag_ids=filters.tag_ids,
            cursor=filters.cursor,
            limit=filters.limit,
        )

        # Convert to response
        data = []
        for transaction in transactions:
            data.append(await self._to_response(transaction))

        return TransactionPage(data=data, next_cursor=next_cursor, has_more=has_more)

    async def update_transaction(
        self, transaction_id: str, user_id: str, data: TransactionUpdate
    ) -> TransactionResponse:
        """Update transaction."""
        transaction = await self.repo.get_by_id(transaction_id, user_id)

        if not transaction:
            raise NotFoundException("Transaction not found")

        old_occurred_at = transaction.occurred_at

        # Update fields
        if data.amount is not None:
            transaction.amount = data.amount

        if data.category_id is not None:
            if data.category_id == "":
                # Unset category
                transaction.category_id = None
            else:
                # Validate category
                category = await self.category_repo.get_by_id(data.category_id, user_id)
                if not category:
                    raise ValidationException("Category not found")
                transaction.category_id = data.category_id

        if data.description is not None:
            transaction.description = data.description

        if data.note is not None:
            transaction.note = data.note

        if data.occurred_at is not None:
            transaction.occurred_at = to_utc(data.occurred_at)

        # Update tags
        if data.tag_ids is not None:
            if data.tag_ids:
                await self.repo.attach_tags(transaction, data.tag_ids)
            else:
                await self.repo.clear_tags(transaction)

        transaction = await self.repo.update(transaction)
        await self.db.commit()

        # Refresh transaction with relationships loaded for response serialization
        result = await self.db.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.tags),
                joinedload(Transaction.receipt),
            )
            .where(Transaction.id == transaction.id)
        )
        transaction = result.unique().scalar_one()

        # Invalidate cache for both old and new months
        await self._invalidate_cache(user_id, old_occurred_at)
        if transaction.occurred_at != old_occurred_at:
            await self._invalidate_cache(user_id, transaction.occurred_at)

        logger.info(f"User {user_id} updated transaction: {transaction_id}")

        return await self._to_response(transaction)

    async def delete_transaction(self, transaction_id: str, user_id: str) -> None:
        """Soft delete transaction."""
        transaction = await self.repo.get_by_id(transaction_id, user_id)

        if not transaction:
            raise NotFoundException("Transaction not found")

        occurred_at = transaction.occurred_at

        await self.repo.soft_delete(transaction)
        await self.db.commit()

        # Invalidate cache
        await self._invalidate_cache(user_id, occurred_at)

        logger.info(f"User {user_id} deleted transaction: {transaction_id}")

    async def get_stats(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category_id: str | None = None,
    ) -> TransactionStats:
        """Get transaction statistics."""
        # Normalize dates
        start_date = to_utc(start_date) if start_date else None
        end_date = to_utc(end_date) if end_date else None

        stats = await self.repo.get_stats(user_id, start_date, end_date, category_id)

        return TransactionStats(**stats)

    async def _to_response(self, transaction: Transaction) -> TransactionResponse:
        """Convert transaction model to response schema."""
        # Get category name
        category_name = None
        if transaction.category:
            category_name = transaction.category.name

        # Get tags
        tags = []
        for tag in transaction.tags:
            tags.append({"id": tag.id, "name": tag.name, "color": tag.color})

        # Check if has receipt (one-to-one relationship)
        # Receipt is eagerly loaded via joinedload in repository queries
        has_receipt = transaction.receipt is not None

        return TransactionResponse(
            id=transaction.id,
            user_id=transaction.user_id,
            category_id=transaction.category_id,
            category_name=category_name,
            amount=transaction.amount,
            currency=transaction.currency,
            type=transaction.type,
            description=transaction.description,
            note=transaction.note,
            occurred_at=transaction.occurred_at,
            tags=tags,
            has_receipt=has_receipt,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )

    async def _invalidate_cache(self, user_id: str, occurred_at: datetime) -> None:
        """Invalidate cache for transaction month."""
        month_key = format_month_key(occurred_at)
        pattern = f"dash:{user_id}:{month_key}*"
        await invalidate_cache_pattern(pattern)
        logger.debug(f"Invalidated cache: {pattern}")

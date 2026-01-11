import logging

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Repository for category database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, category_id: str, user_id: str) -> Category | None:
        """Get category by ID and user ID."""
        result = await self.db.execute(
            select(Category).where(and_(Category.id == category_id, Category.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(
        self,
        user_id: str,
        category_type: str | None = None,
    ) -> list[Category]:
        """
        Get all categories for a user.

        Args:
            user_id: User ID
            category_type: Optional filter by type (expense/income)
        """
        query = select(Category).where(Category.user_id == user_id)

        if category_type:
            query = query.where(Category.type == category_type)

        query = query.order_by(Category.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, category: Category) -> Category:
        """Create new category."""
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        logger.info(f"Created category: {category.id} ({category.name})")
        return category

    async def update(self, category: Category) -> Category:
        """Update existing category."""
        await self.db.flush()
        await self.db.refresh(category)
        logger.info(f"Updated category: {category.id}")
        return category

    async def delete(self, category: Category) -> None:
        """Delete category."""
        await self.db.delete(category)
        await self.db.flush()
        logger.info(f"Deleted category: {category.id}")

    async def name_exists(
        self,
        user_id: str,
        name: str,
        exclude_id: str | None = None,
    ) -> bool:
        """
        Check if category name already exists for user.

        Args:
            user_id: User ID
            name: Category name to check
            exclude_id: Optional category ID to exclude from check (for updates)
        """
        query = select(Category.id).where(and_(Category.user_id == user_id, Category.name == name))

        if exclude_id:
            query = query.where(Category.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_transaction_count(self, category_id: str) -> int:
        """Get count of active transactions in category."""
        result = await self.db.execute(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.category_id == category_id,
                    Transaction.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one()

    async def get_counts_by_type(self, user_id: str) -> dict[str, int]:
        """Get category counts by type."""
        result = await self.db.execute(
            select(Category.type, func.count(Category.id).label("count"))
            .where(Category.user_id == user_id)
            .group_by(Category.type)
        )

        counts: dict[str, int] = {"expense": 0, "income": 0}
        for row in result:
            counts[row.type] = row.count

        return counts

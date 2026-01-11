import logging

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, transaction_tags
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class TagRepository:
    """Repository for tag database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tag_id: str, user_id: str) -> Tag | None:
        """Get tag by ID and user ID."""
        result = await self.db.execute(
            select(Tag).where(and_(Tag.id == tag_id, Tag.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: str) -> list[Tag]:
        """Get all tags for a user."""
        result = await self.db.execute(select(Tag).where(Tag.user_id == user_id).order_by(Tag.name))
        return list(result.scalars().all())

    async def create(self, tag: Tag) -> Tag:
        """Create new tag."""
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        logger.info(f"Created tag: {tag.id} ({tag.name})")
        return tag

    async def update(self, tag: Tag) -> Tag:
        """Update existing tag."""
        await self.db.flush()
        await self.db.refresh(tag)
        logger.info(f"Updated tag: {tag.id}")
        return tag

    async def delete(self, tag: Tag) -> None:
        """Delete tag."""
        await self.db.delete(tag)
        await self.db.flush()
        logger.info(f"Deleted tag: {tag.id}")

    async def name_exists(
        self,
        user_id: str,
        name: str,
        exclude_id: str | None = None,
    ) -> bool:
        """Check if tag name already exists for user."""
        query = select(Tag.id).where(and_(Tag.user_id == user_id, Tag.name == name))

        if exclude_id:
            query = query.where(Tag.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_transaction_count(self, tag_id: str) -> int:
        """Get count of active transactions with this tag."""
        result = await self.db.execute(
            select(func.count(transaction_tags.c.transaction_id))
            .select_from(transaction_tags)
            .join(Transaction, Transaction.id == transaction_tags.c.transaction_id)
            .where(
                and_(
                    transaction_tags.c.tag_id == tag_id,
                    Transaction.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one()

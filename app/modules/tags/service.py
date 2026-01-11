import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.tag import Tag
from app.modules.tags.repo import TagRepository
from app.modules.tags.schemas import TagCreate, TagList, TagResponse, TagUpdate

logger = logging.getLogger(__name__)


class TagService:
    """Service for tag business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TagRepository(db)

    async def create_tag(self, user_id: str, data: TagCreate) -> TagResponse:
        """Create new tag."""
        # Check for duplicate name
        if await self.repo.name_exists(user_id, data.name):
            raise ConflictException(f"Tag '{data.name}' already exists")

        # Create tag
        tag = Tag(
            user_id=user_id,
            name=data.name,
            color=data.color,
        )

        tag = await self.repo.create(tag)
        await self.db.commit()

        logger.info(f"User {user_id} created tag: {tag.name}")

        return await self._to_response(tag)

    async def get_tag(self, tag_id: str, user_id: str) -> TagResponse:
        """Get tag by ID."""
        tag = await self.repo.get_by_id(tag_id, user_id)

        if not tag:
            raise NotFoundException("Tag not found")

        return await self._to_response(tag)

    async def list_tags(self, user_id: str) -> TagList:
        """List all tags for user."""
        tags = await self.repo.get_all_by_user(user_id)

        items = []
        for tag in tags:
            items.append(await self._to_response(tag))

        return TagList(items=items, total=len(items))

    async def update_tag(
        self,
        tag_id: str,
        user_id: str,
        data: TagUpdate,
    ) -> TagResponse:
        """Update tag."""
        tag = await self.repo.get_by_id(tag_id, user_id)

        if not tag:
            raise NotFoundException("Tag not found")

        # Check for name conflict
        if data.name and data.name != tag.name:
            if await self.repo.name_exists(user_id, data.name, tag_id):
                raise ConflictException(f"Tag '{data.name}' already exists")
            tag.name = data.name

        if data.color is not None:
            tag.color = data.color

        tag = await self.repo.update(tag)
        await self.db.commit()

        logger.info(f"User {user_id} updated tag: {tag.id}")

        return await self._to_response(tag)

    async def delete_tag(self, tag_id: str, user_id: str) -> None:
        """Delete tag (cascade removes from transactions)."""
        tag = await self.repo.get_by_id(tag_id, user_id)

        if not tag:
            raise NotFoundException("Tag not found")

        await self.repo.delete(tag)
        await self.db.commit()

        logger.info(f"User {user_id} deleted tag: {tag_id}")

    async def _to_response(self, tag: Tag) -> TagResponse:
        """Convert tag model to response schema."""
        transaction_count = await self.repo.get_transaction_count(tag.id)

        return TagResponse(
            id=tag.id,
            user_id=tag.user_id,
            name=tag.name,
            color=tag.color,
            created_at=tag.created_at,
            transaction_count=transaction_count,
        )

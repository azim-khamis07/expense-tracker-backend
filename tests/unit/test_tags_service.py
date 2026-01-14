"""Unit tests for tags service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundException
from app.modules.tags.schemas import TagCreate, TagUpdate
from app.modules.tags.service import TagService


class TestTagService:
    """Test TagService methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create tag service instance."""
        return TagService(mock_db)

    @pytest.fixture
    def mock_repo(self, service):
        """Mock tag repository."""
        return service.repo

    @pytest.mark.asyncio
    async def test_create_tag_success(self, service, mock_repo):
        """Test successful tag creation."""
        from app.models.tag import Tag

        mock_tag = Tag(
            id="tag123",
            user_id="user123",
            name="urgent",
            color="#FF0000",
            created_at=datetime.now(UTC),
        )
        mock_repo.create = AsyncMock(return_value=mock_tag)
        mock_repo.name_exists = AsyncMock(return_value=False)
        mock_repo.get_transaction_count = AsyncMock(return_value=0)

        tag_response = await service.create_tag(
            "user123", TagCreate(name="urgent", color="#FF0000")
        )

        assert tag_response.id == "tag123"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tag_duplicate(self, service, mock_repo):
        """Test creating duplicate tag raises exception."""
        from app.core.exceptions import ConflictException

        mock_repo.name_exists = AsyncMock(return_value=True)

        with pytest.raises(ConflictException, match="already exists"):
            await service.create_tag("user123", TagCreate(name="urgent", color="#FF0000"))

    @pytest.mark.asyncio
    async def test_get_tag_success(self, service, mock_repo):
        """Test getting tag by ID."""
        from app.models.tag import Tag

        mock_tag = Tag(
            id="tag123",
            user_id="user123",
            name="urgent",
            color="#FF0000",
            created_at=datetime.now(UTC),
        )
        mock_repo.get_by_id = AsyncMock(return_value=mock_tag)
        mock_repo.get_transaction_count = AsyncMock(return_value=0)

        tag_response = await service.get_tag("tag123", "user123")

        assert tag_response.id == "tag123"
        mock_repo.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tag_not_found(self, service, mock_repo):
        """Test getting non-existent tag raises exception."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException, match="Tag not found"):
            await service.get_tag("user123", "nonexistent")

    @pytest.mark.asyncio
    async def test_update_tag_success(self, service, mock_repo):
        """Test successful tag update."""
        from app.models.tag import Tag

        mock_tag = Tag(
            id="tag123",
            user_id="user123",
            name="urgent",
            color="#FF0000",
            created_at=datetime.now(UTC),
        )
        mock_repo.get_by_id = AsyncMock(return_value=mock_tag)
        mock_repo.name_exists = AsyncMock(return_value=False)
        mock_repo.update = AsyncMock(return_value=mock_tag)
        mock_repo.get_transaction_count = AsyncMock(return_value=0)

        updated_tag = await service.update_tag(
            "tag123", "user123", TagUpdate(name="updated", color="#00FF00")
        )

        assert updated_tag.id == "tag123"
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tag_success(self, service, mock_repo):
        """Test successful tag deletion."""
        mock_tag = AsyncMock()
        mock_tag.id = "tag123"
        mock_tag.user_id = "user123"
        mock_repo.get_by_id = AsyncMock(return_value=mock_tag)
        mock_repo.delete = AsyncMock()

        await service.delete_tag("user123", "tag123")

        mock_repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tags(self, service, mock_repo):
        """Test listing tags."""
        from app.models.tag import Tag

        now = datetime.now(UTC)
        mock_tags = [
            Tag(id="tag1", user_id="user123", name="tag1", color="#FF0000", created_at=now),
            Tag(id="tag2", user_id="user123", name="tag2", color="#00FF00", created_at=now),
        ]
        mock_repo.get_all_by_user = AsyncMock(return_value=mock_tags)
        mock_repo.get_transaction_count = AsyncMock(return_value=0)

        tag_list = await service.list_tags("user123")

        assert len(tag_list.items) == 2
        assert tag_list.total == 2
        mock_repo.get_all_by_user.assert_called_once()

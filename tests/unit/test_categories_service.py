"""Unit tests for categories service."""

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundException
from app.modules.categories.schemas import CategoryCreate, CategoryUpdate
from app.modules.categories.service import CategoryService


class TestCategoryService:
    """Test CategoryService methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create category service instance."""
        return CategoryService(mock_db)

    @pytest.fixture
    def mock_repo(self, service):
        """Mock category repository."""
        return service.repo

    @pytest.mark.asyncio
    async def test_create_category_success(self, service, mock_repo):
        """Test successful category creation."""
        mock_category = AsyncMock()
        mock_category.id = "cat123"
        mock_category.name = "Food"
        mock_repo.create = AsyncMock(return_value=mock_category)
        mock_repo.get_by_name_and_user = AsyncMock(return_value=None)

        category_response = await service.create_category(
            "user123", CategoryCreate(name="Food", type="expense", description="Food expenses")
        )

        assert category_response.id == "cat123"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_category_duplicate(self, service, mock_repo):
        """Test creating duplicate category raises exception."""
        from app.core.exceptions import ConflictException

        mock_repo.name_exists = AsyncMock(return_value=True)

        with pytest.raises(ConflictException, match="already exists"):
            await service.create_category("user123", CategoryCreate(name="Food", type="expense"))

    @pytest.mark.asyncio
    async def test_get_category_success(self, service, mock_repo):
        """Test getting category by ID."""
        mock_category = AsyncMock()
        mock_category.id = "cat123"
        mock_repo.get_by_id = AsyncMock(return_value=mock_category)

        category_response = await service.get_category("cat123", "user123")

        assert category_response.id == "cat123"
        mock_repo.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_not_found(self, service, mock_repo):
        """Test getting non-existent category raises exception."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException, match="Category not found"):
            await service.get_category("user123", "nonexistent")

    @pytest.mark.asyncio
    async def test_update_category_success(self, service, mock_repo):
        """Test successful category update."""
        mock_category = AsyncMock()
        mock_category.id = "cat123"
        mock_category.user_id = "user123"
        mock_repo.get_by_id = AsyncMock(return_value=mock_category)
        mock_repo.name_exists = AsyncMock(return_value=False)
        mock_repo.update = AsyncMock(return_value=mock_category)
        mock_repo.get_transaction_count = AsyncMock(return_value=0)

        updated_category = await service.update_category(
            "user123", "cat123", CategoryUpdate(name="Updated Food")
        )

        assert updated_category.id == "cat123"
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_category_success(self, service, mock_repo):
        """Test successful category deletion."""
        mock_category = AsyncMock()
        mock_category.id = "cat123"
        mock_category.user_id = "user123"
        mock_repo.get_by_id = AsyncMock(return_value=mock_category)
        mock_repo.delete = AsyncMock()

        await service.delete_category("user123", "cat123")

        mock_repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_categories(self, service, mock_repo):
        """Test listing categories."""

        mock_categories = [AsyncMock(), AsyncMock()]
        for cat in mock_categories:
            cat.id = "cat123"
            cat.name = "Food"
            cat.type = "expense"
        mock_repo.get_all_by_user = AsyncMock(return_value=mock_categories)
        mock_repo.get_counts_by_type = AsyncMock(return_value={"expense": 1, "income": 0})
        mock_repo.get_transaction_count = AsyncMock(return_value=0)

        category_list = await service.list_categories("user123")

        assert category_list.total == 2
        assert len(category_list.items) == 2
        mock_repo.get_all_by_user.assert_called_once()

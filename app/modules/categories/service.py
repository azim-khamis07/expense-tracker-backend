import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.infra.redis import invalidate_cache_pattern
from app.models.category import Category
from app.modules.categories.repo import CategoryRepository
from app.modules.categories.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryResponse,
    CategoryUpdate,
)

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for category business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CategoryRepository(db)

    async def create_category(self, user_id: str, data: CategoryCreate) -> CategoryResponse:
        """
        Create new category.

        Raises:
            ConflictException: If category name already exists for user
        """
        # Check for duplicate name
        if await self.repo.name_exists(user_id, data.name):
            raise ConflictException(f"Category '{data.name}' already exists")

        # Create category
        category = Category(
            user_id=user_id,
            name=data.name,
            type=data.type,
            description=data.description,
        )

        category = await self.repo.create(category)
        await self.db.commit()

        logger.info(f"User {user_id} created category: {category.name}")

        return await self._to_response(category)

    async def get_category(self, category_id: str, user_id: str) -> CategoryResponse:
        """
        Get category by ID.

        Raises:
            NotFoundException: If category not found or doesn't belong to user
        """
        category = await self.repo.get_by_id(category_id, user_id)

        if not category:
            raise NotFoundException("Category not found")

        return await self._to_response(category)

    async def list_categories(
        self,
        user_id: str,
        category_type: str | None = None,
    ) -> CategoryList:
        """
        List all categories for user.

        Args:
            user_id: User ID
            category_type: Optional filter by type
        """
        categories = await self.repo.get_all_by_user(user_id, category_type)

        # Get counts by type
        counts = await self.repo.get_counts_by_type(user_id)

        # Convert to response with transaction counts
        items = []
        for category in categories:
            items.append(await self._to_response(category))

        return CategoryList(
            items=items,
            total=len(items),
            expense_count=counts["expense"],
            income_count=counts["income"],
        )

    async def update_category(
        self,
        category_id: str,
        user_id: str,
        data: CategoryUpdate,
    ) -> CategoryResponse:
        """
        Update category.

        Raises:
            NotFoundException: If category not found
            ConflictException: If new name conflicts with existing category
        """
        category = await self.repo.get_by_id(category_id, user_id)

        if not category:
            raise NotFoundException("Category not found")

        # Check for name conflict (if name is being changed)
        if data.name and data.name != category.name:
            if await self.repo.name_exists(user_id, data.name, category_id):
                raise ConflictException(f"Category '{data.name}' already exists")
            category.name = data.name

        # Update description
        if data.description is not None:
            category.description = data.description

        # Update timestamp (model has onupdate, but ensure it's set)
        category.updated_at = datetime.now(UTC)

        category = await self.repo.update(category)
        await self.db.commit()

        # Invalidate dashboard cache (category names might be displayed)
        await invalidate_cache_pattern(f"dash:{user_id}:*")

        logger.info(f"User {user_id} updated category: {category.id}")

        return await self._to_response(category)

    async def delete_category(self, category_id: str, user_id: str) -> None:
        """
        Delete category.

        Raises:
            NotFoundException: If category not found
            ValidationException: If category has transactions
        """
        category = await self.repo.get_by_id(category_id, user_id)

        if not category:
            raise NotFoundException("Category not found")

        # Check if category has transactions
        transaction_count = await self.repo.get_transaction_count(category_id)

        if transaction_count > 0:
            raise ValidationException(
                f"Cannot delete category with {transaction_count} transaction(s). "
                "Please reassign or delete the transactions first."
            )

        await self.repo.delete(category)
        await self.db.commit()

        logger.info(f"User {user_id} deleted category: {category_id}")

    async def _to_response(self, category: Category) -> CategoryResponse:
        """Convert category model to response schema."""
        transaction_count = await self.repo.get_transaction_count(category.id)

        return CategoryResponse(
            id=category.id,
            user_id=category.user_id,
            name=category.name,
            type=category.type,
            description=category.description,
            created_at=category.created_at,
            updated_at=category.updated_at,
            transaction_count=transaction_count,
        )

    async def create_default_categories(self, user_id: str) -> list[CategoryResponse]:
        """Create default categories for new user."""
        default_categories = [
            # Expense categories
            CategoryCreate(
                name="Groceries", type="expense", description="Food and household items"
            ),
            CategoryCreate(name="Transport", type="expense", description="Transportation costs"),
            CategoryCreate(name="Utilities", type="expense", description="Bills and utilities"),
            CategoryCreate(name="Entertainment", type="expense", description="Movies, games, etc."),
            CategoryCreate(name="Healthcare", type="expense", description="Medical expenses"),
            CategoryCreate(name="Shopping", type="expense", description="General shopping"),
            CategoryCreate(name="Dining", type="expense", description="Restaurants and cafes"),
            CategoryCreate(
                name="Other Expenses", type="expense", description="Miscellaneous expenses"
            ),
            # Income categories
            CategoryCreate(name="Salary", type="income", description="Monthly salary"),
            CategoryCreate(name="Freelance", type="income", description="Freelance income"),
            CategoryCreate(name="Investment", type="income", description="Investment returns"),
            CategoryCreate(name="Other Income", type="income", description="Miscellaneous income"),
        ]

        created = []
        for cat_data in default_categories:
            try:
                category = await self.create_category(user_id, cat_data)
                created.append(category)
            except ConflictException:
                # Skip if already exists
                pass

        logger.info(f"Created {len(created)} default categories for user {user_id}")
        return created

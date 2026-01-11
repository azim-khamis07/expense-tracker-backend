from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.categories.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryResponse,
    CategoryUpdate,
)
from app.modules.categories.service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new expense or income category",
)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new category.

    - **name**: Category name (unique per user)
    - **type**: 'expense' or 'income'
    - **description**: Optional description
    """
    service = CategoryService(db)
    return await service.create_category(current_user.id, data)


@router.get(
    "",
    response_model=CategoryList,
    summary="List categories",
    description="Get all categories for current user",
)
async def list_categories(
    type: str | None = Query(None, description="Filter by type (expense or income)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all categories.

    Optionally filter by type (expense/income).
    """
    service = CategoryService(db)
    return await service.list_categories(current_user.id, type)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category",
    description="Get category by ID",
)
async def get_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get category by ID."""
    service = CategoryService(db)
    return await service.get_category(category_id, current_user.id)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
    description="Update category name or description",
)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update category.

    Can update name and/or description. Type cannot be changed.
    """
    service = CategoryService(db)
    return await service.update_category(category_id, current_user.id, data)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
    description="Delete category (only if no transactions)",
)
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete category.

    Cannot delete if category has transactions.
    """
    service = CategoryService(db)
    await service.delete_category(category_id, current_user.id)
    return None


@router.post(
    "/defaults",
    response_model=CategoryList,
    status_code=status.HTTP_201_CREATED,
    summary="Create default categories",
    description="Create a set of default categories",
)
async def create_default_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create default categories.

    Creates a set of common expense and income categories.
    Useful for new users to get started quickly.
    """
    service = CategoryService(db)
    await service.create_default_categories(current_user.id)

    # Return full list
    return await service.list_categories(current_user.id)

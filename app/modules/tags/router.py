from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.tags.schemas import TagCreate, TagList, TagResponse, TagUpdate
from app.modules.tags.service import TagService

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
)
async def create_tag(
    data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    service = TagService(db)
    return await service.create_tag(current_user.id, data)


@router.get(
    "",
    response_model=TagList,
    summary="List tags",
)
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tags."""
    service = TagService(db)
    return await service.list_tags(current_user.id)


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Get tag",
)
async def get_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tag by ID."""
    service = TagService(db)
    return await service.get_tag(tag_id, current_user.id)


@router.put(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update tag",
)
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tag."""
    service = TagService(db)
    return await service.update_tag(tag_id, current_user.id, data)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tag",
)
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete tag."""
    service = TagService(db)
    await service.delete_tag(tag_id, current_user.id)
    return None

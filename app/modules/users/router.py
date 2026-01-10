import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationException
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.modules.auth.schemas import MessageResponse
from app.modules.users.repo import UserRepository
from app.modules.users.schemas import ChangePasswordRequest, UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/profile",
    response_model=UserProfile,
    summary="Get user profile",
    description="Get detailed profile of current user",
)
async def get_profile(current_user: User = Depends(get_current_user)) -> UserProfile:
    """Get current user's detailed profile."""
    return UserProfile.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change current user's password",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Change password.

    Requires current password for verification.
    """
    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        raise ValidationException("Current password is incorrect")

    # Update password
    repo = UserRepository(db)
    new_password_hash = hash_password(data.new_password)
    await repo.update_password(current_user, new_password_hash)

    logger.info(f"Password changed for user: {current_user.email}")

    return MessageResponse(message="Password changed successfully")


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
    description="Delete current user's account (permanent)",
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete user account.

    This is permanent and cannot be undone.
    All user data will be deleted due to CASCADE foreign keys.
    """
    repo = UserRepository(db)
    await repo.delete(current_user)

    logger.info(f"Account deleted for user: {current_user.email}")

    return None

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        return user is not None

    async def create(self, user: User) -> User:
        """Create new user."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"User created: {user.email} (id: {user.id})")
        return user

    async def update(self, user: User) -> User:
        """Update user."""
        user.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        logger.debug(f"User updated: {user.email} (id: {user.id})")
        return user

    async def set_email_verified(self, user: User) -> User:
        """Mark user email as verified and clear verification token."""
        user.is_email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None
        user.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Email verified for user: {user.email} (id: {user.id})")
        return user

    async def set_password_reset_token(self, user: User, token: str, expires_at: datetime) -> User:
        """Set password reset token for user."""
        user.password_reset_token = token
        user.password_reset_token_expires = expires_at
        user.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Password reset token set for user: {user.email} (id: {user.id})")
        return user

    async def update_password(self, user: User, password_hash: str) -> User:
        """Update user password."""
        user.password_hash = password_hash
        user.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Password updated for user: {user.email} (id: {user.id})")
        return user

    async def clear_password_reset_token(self, user: User) -> User:
        """Clear password reset token from user."""
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        logger.debug(f"Password reset token cleared for user: {user.email} (id: {user.id})")
        return user

    async def delete(self, user: User) -> None:
        """Delete user from database (hard delete)."""
        self.db.delete(user)
        await self.db.commit()
        logger.warning(f"User deleted: {user.email} (id: {user.id})")

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_email_token,
    verify_password,
    verify_password_reset_token,
)
from app.models.user import User
from app.modules.auth.schemas import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.modules.users.repo import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: UserRegisterRequest) -> tuple[User, str]:
        """
        Register new user.

        Returns:
            Tuple of (user, email_verification_token)

        Raises:
            ConflictException: If email already exists
        """
        # Check if email already exists
        if await self.user_repo.email_exists(data.email):
            raise ConflictException("Email already registered")

        # Create user
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            is_email_verified=False,
            is_active=True,
        )

        # Generate email verification token
        verification_token = create_email_verification_token(data.email)
        user.email_verification_token = verification_token
        user.email_verification_token_expires = datetime.now(UTC) + timedelta(hours=24)

        # Save user
        user = await self.user_repo.create(user)

        logger.info(f"User registered: {user.email}")

        return user, verification_token

    async def login(self, data: UserLoginRequest) -> TokenResponse:
        """
        Authenticate user and return tokens.

        Raises:
            UnauthorizedException: If credentials are invalid
        """
        # Get user by email
        user = await self.user_repo.get_by_email(data.email)

        if not user:
            raise UnauthorizedException("Invalid email or password")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            logger.warning(f"Failed login attempt for: {data.email}")
            raise UnauthorizedException("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise UnauthorizedException("Account is inactive")

        # Create tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access token from refresh token.

        Raises:
            UnauthorizedException: If refresh token is invalid
        """
        try:
            # Decode refresh token
            payload = decode_token(refresh_token)

            # Verify token type
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid token type")

            # Extract user ID
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedException("Invalid token payload")

            # Verify user exists and is active
            user = await self.user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise UnauthorizedException("User not found or inactive")

            # Create new access token
            new_access_token = create_access_token({"sub": user_id})

            logger.info(f"Access token refreshed for user: {user.email}")

            return TokenResponse(
                access_token=new_access_token,
                refresh_token=refresh_token,  # Return same refresh token
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            raise UnauthorizedException("Invalid refresh token") from e

    async def verify_email(self, token: str) -> User:
        """
        Verify user email with token.

        Raises:
            ValidationException: If token is invalid or expired
        """
        # Verify token
        email = verify_email_token(token)
        if not email:
            raise ValidationException("Invalid or expired verification token")

        # Get user
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundException("User not found")

        # Check if already verified
        if user.is_email_verified:
            return user

        # Check token matches and not expired
        if user.email_verification_token != token:
            raise ValidationException("Invalid verification token")

        if (
            user.email_verification_token_expires
            and user.email_verification_token_expires < datetime.now(UTC)
        ):
            raise ValidationException("Verification token expired")

        # Mark as verified
        user = await self.user_repo.set_email_verified(user)

        logger.info(f"Email verified for user: {user.email}")

        return user

    async def resend_verification_email(self, email: str) -> str:
        """
        Resend email verification token.

        Returns:
            New verification token

        Raises:
            NotFoundException: If user not found
            ValidationException: If email already verified
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundException("User not found")

        if user.is_email_verified:
            raise ValidationException("Email already verified")

        # Generate new token
        verification_token = create_email_verification_token(email)
        user.email_verification_token = verification_token
        user.email_verification_token_expires = datetime.now(UTC) + timedelta(hours=24)

        await self.user_repo.update(user)

        logger.info(f"Verification email resent to: {email}")

        return verification_token

    async def request_password_reset(self, email: str) -> str | None:
        """
        Request password reset.
        Returns token if user exists, None otherwise (don't reveal if email exists).
        """
        user = await self.user_repo.get_by_email(email)

        if not user:
            # Don't reveal that email doesn't exist
            logger.info(f"Password reset requested for non-existent email: {email}")
            return None

        # Generate reset token
        reset_token = create_password_reset_token(email)
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await self.user_repo.set_password_reset_token(user, reset_token, expires_at)

        logger.info(f"Password reset requested for: {email}")

        return reset_token

    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset password with token.

        Raises:
            ValidationException: If token is invalid or expired
        """
        # Verify token
        email = verify_password_reset_token(token)
        if not email:
            raise ValidationException("Invalid or expired reset token")

        # Get user
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundException("User not found")

        # Check token matches and not expired
        if user.password_reset_token != token:
            raise ValidationException("Invalid reset token")

        if user.password_reset_token_expires and user.password_reset_token_expires < datetime.now(
            UTC
        ):
            raise ValidationException("Reset token expired")

        # Update password
        new_password_hash = hash_password(new_password)
        await self.user_repo.update_password(user, new_password_hash)

        # Clear reset token
        await self.user_repo.clear_password_reset_token(user)

        logger.info(f"Password reset for user: {user.email}")

        return user

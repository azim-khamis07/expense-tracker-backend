from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.core.security import (
    create_password_reset_token,
    decode_token,
)
from app.modules.auth.schemas import UserLoginRequest, UserRegisterRequest
from app.modules.auth.service import AuthService


@pytest.mark.asyncio
class TestAuthService:
    """Test authentication service."""

    async def test_register_success(self, db_session):
        """Test successful user registration."""
        service = AuthService(db_session)

        data = UserRegisterRequest(
            email="newuser@example.com",
            password="SecurePass123!",
        )

        user, token = await service.register(data)

        assert user.email == "newuser@example.com"
        assert user.is_email_verified is False
        assert user.is_active is True
        assert token is not None
        assert len(token) > 0

    async def test_register_duplicate_email(self, db_session):
        """Test registration with duplicate email."""
        service = AuthService(db_session)

        # Register first user
        data = UserRegisterRequest(
            email="duplicate@example.com",
            password="SecurePass123!",
        )
        await service.register(data)

        # Try to register with same email
        with pytest.raises(ConflictException):
            await service.register(data)

    async def test_login_success(self, db_session):
        """Test successful login."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="loginuser@example.com",
            password="SecurePass123!",
        )
        await service.register(register_data)

        # Login
        login_data = UserLoginRequest(
            email="loginuser@example.com",
            password="SecurePass123!",
        )
        tokens = await service.login(login_data)

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0

    async def test_login_invalid_password(self, db_session):
        """Test login with wrong password."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="wrongpass@example.com",
            password="SecurePass123!",
        )
        await service.register(register_data)

        # Try login with wrong password
        login_data = UserLoginRequest(
            email="wrongpass@example.com",
            password="WrongPassword123!",
        )

        with pytest.raises(UnauthorizedException):
            await service.login(login_data)

    async def test_login_nonexistent_user(self, db_session):
        """Test login with non-existent email."""
        service = AuthService(db_session)

        login_data = UserLoginRequest(
            email="nonexistent@example.com",
            password="SomePassword123!",
        )

        with pytest.raises(UnauthorizedException):
            await service.login(login_data)

    async def test_login_inactive_user(self, db_session):
        """Test login with inactive user account."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="inactive@example.com",
            password="SecurePass123!",
        )
        user, _ = await service.register(register_data)

        # Deactivate user
        user.is_active = False
        await db_session.commit()

        # Try to login
        login_data = UserLoginRequest(
            email="inactive@example.com",
            password="SecurePass123!",
        )

        with pytest.raises(UnauthorizedException):
            await service.login(login_data)

    async def test_refresh_access_token_success(self, db_session):
        """Test successful token refresh."""
        import asyncio

        service = AuthService(db_session)

        # Register and login user
        register_data = UserRegisterRequest(
            email="refreshtest@example.com",
            password="SecurePass123!",
        )
        await service.register(register_data)

        login_data = UserLoginRequest(
            email="refreshtest@example.com",
            password="SecurePass123!",
        )
        login_tokens = await service.login(login_data)

        # Small delay to ensure different token timestamps
        await asyncio.sleep(1)

        # Refresh token
        refreshed_tokens = await service.refresh_access_token(login_tokens.refresh_token)

        assert refreshed_tokens.access_token is not None
        assert refreshed_tokens.refresh_token == login_tokens.refresh_token  # Same refresh token
        assert refreshed_tokens.token_type == "bearer"

        # Verify tokens are valid by decoding them
        original_payload = decode_token(login_tokens.access_token)
        refreshed_payload = decode_token(refreshed_tokens.access_token)

        assert original_payload["sub"] == refreshed_payload["sub"]  # Same user
        assert original_payload["type"] == "access"
        assert refreshed_payload["type"] == "access"

    async def test_refresh_access_token_invalid(self, db_session):
        """Test token refresh with invalid refresh token."""
        service = AuthService(db_session)

        with pytest.raises(UnauthorizedException):
            await service.refresh_access_token("invalid.token.here")

    async def test_refresh_access_token_wrong_type(self, db_session):
        """Test token refresh with access token (wrong type)."""
        service = AuthService(db_session)

        # Register and login user
        register_data = UserRegisterRequest(
            email="wrongtype@example.com",
            password="SecurePass123!",
        )
        await service.register(register_data)

        login_data = UserLoginRequest(
            email="wrongtype@example.com",
            password="SecurePass123!",
        )
        login_tokens = await service.login(login_data)

        # Try to refresh with access token (should fail)
        with pytest.raises(UnauthorizedException):
            await service.refresh_access_token(login_tokens.access_token)

    async def test_verify_email_success(self, db_session):
        """Test successful email verification."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="verify@example.com",
            password="SecurePass123!",
        )
        user, verification_token = await service.register(register_data)

        assert user.is_email_verified is False

        # Verify email
        verified_user = await service.verify_email(verification_token)

        assert verified_user.is_email_verified is True
        assert verified_user.email == "verify@example.com"

    async def test_verify_email_already_verified(self, db_session):
        """Test email verification when already verified."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="alreadyverified@example.com",
            password="SecurePass123!",
        )
        user, verification_token = await service.register(register_data)

        # Verify first time
        await service.verify_email(verification_token)

        # Verify again (should be idempotent)
        verified_user = await service.verify_email(verification_token)
        assert verified_user.is_email_verified is True

    async def test_verify_email_invalid_token(self, db_session):
        """Test email verification with invalid token."""
        service = AuthService(db_session)

        with pytest.raises(ValidationException):
            await service.verify_email("invalid.token.here")

    async def test_resend_verification_email_success(self, db_session):
        """Test resending verification email."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="resend@example.com",
            password="SecurePass123!",
        )
        await service.register(register_data)

        # Resend verification
        new_token = await service.resend_verification_email("resend@example.com")

        assert new_token is not None
        assert len(new_token) > 0

    async def test_resend_verification_email_already_verified(self, db_session):
        """Test resending verification email when already verified."""
        service = AuthService(db_session)

        # Register and verify user
        register_data = UserRegisterRequest(
            email="resendverified@example.com",
            password="SecurePass123!",
        )
        user, token = await service.register(register_data)
        await service.verify_email(token)

        # Try to resend (should fail)
        with pytest.raises(ValidationException):
            await service.resend_verification_email("resendverified@example.com")

    async def test_resend_verification_email_not_found(self, db_session):
        """Test resending verification email for non-existent user."""
        service = AuthService(db_session)

        with pytest.raises(NotFoundException):
            await service.resend_verification_email("nonexistent@example.com")

    async def test_request_password_reset_success(self, db_session):
        """Test successful password reset request."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="reset@example.com",
            password="SecurePass123!",
        )
        await service.register(register_data)

        # Request password reset
        reset_token = await service.request_password_reset("reset@example.com")

        assert reset_token is not None
        assert len(reset_token) > 0

    async def test_request_password_reset_nonexistent_user(self, db_session):
        """Test password reset request for non-existent user (should return None)."""
        service = AuthService(db_session)

        # Request reset for non-existent user
        reset_token = await service.request_password_reset("notexist@example.com")

        # Should return None (don't reveal if email exists)
        assert reset_token is None

    async def test_reset_password_success(self, db_session):
        """Test successful password reset."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="resetpass@example.com",
            password="OldPassword123!",
        )
        await service.register(register_data)

        # Request password reset
        reset_token = await service.request_password_reset("resetpass@example.com")
        assert reset_token is not None

        # Reset password
        reset_user = await service.reset_password(reset_token, "NewPassword123!")

        assert reset_user.email == "resetpass@example.com"

        # Verify new password works
        login_data = UserLoginRequest(
            email="resetpass@example.com",
            password="NewPassword123!",
        )
        tokens = await service.login(login_data)
        assert tokens.access_token is not None

    async def test_reset_password_invalid_token(self, db_session):
        """Test password reset with invalid token."""
        service = AuthService(db_session)

        with pytest.raises(ValidationException):
            await service.reset_password("invalid.token.here", "NewPassword123!")

    async def test_reset_password_expired_token(self, db_session):
        """Test password reset with expired token."""
        service = AuthService(db_session)

        # Register user
        register_data = UserRegisterRequest(
            email="expiredtoken@example.com",
            password="SecurePass123!",
        )
        user, _ = await service.register(register_data)

        # Create expired token manually
        from app.modules.users.repo import UserRepository

        repo = UserRepository(db_session)
        expired_token = create_password_reset_token(user.email)
        expired_date = datetime.now(UTC) - timedelta(hours=2)  # 2 hours ago (expired)
        await repo.set_password_reset_token(user, expired_token, expired_date)

        # Try to reset with expired token
        with pytest.raises(ValidationException):
            await service.reset_password(expired_token, "NewPassword123!")

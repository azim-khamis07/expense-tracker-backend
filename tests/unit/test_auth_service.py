"""Unit tests for auth service."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ConflictException, UnauthorizedException, ValidationException
from app.core.security import create_email_verification_token, create_refresh_token
from app.modules.auth.schemas import UserLoginRequest, UserRegisterRequest
from app.modules.auth.service import AuthService
from app.modules.users.repo import UserRepository


@pytest.mark.unit
@pytest.mark.auth
class TestAuthService:
    """Test authentication service methods."""

    @pytest.mark.asyncio
    async def test_register_success(self, db_session):
        """Test successful user registration."""
        service = AuthService(db_session)

        data = UserRegisterRequest(email="newuser@example.com", password="SecurePass123!")
        user, verification_token = await service.register(data)

        assert user.email == "newuser@example.com"
        assert not user.is_email_verified
        assert user.password_hash is not None
        assert user.password_hash != "SecurePass123!"  # Should be hashed
        assert verification_token is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, db_session, test_user):
        """Test registration with duplicate email."""
        service = AuthService(db_session)

        data = UserRegisterRequest(email=test_user.email, password="SecurePass123!")

        with pytest.raises(ConflictException):
            await service.register(data)

    @pytest.mark.asyncio
    async def test_login_success(self, db_session, test_user):
        """Test successful login."""
        service = AuthService(db_session)

        data = UserLoginRequest(email=test_user.email, password="Test1234!")
        result = await service.login(data)

        assert "access_token" in result.model_dump()
        assert "refresh_token" in result.model_dump()
        assert result.token_type == "bearer"
        assert result.expires_in > 0

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, db_session):
        """Test login with invalid email."""
        service = AuthService(db_session)

        data = UserLoginRequest(email="nonexistent@example.com", password="Test1234!")

        with pytest.raises(UnauthorizedException):
            await service.login(data)

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, db_session, test_user):
        """Test login with invalid password."""
        service = AuthService(db_session)

        data = UserLoginRequest(email=test_user.email, password="WrongPassword123!")

        with pytest.raises(UnauthorizedException):
            await service.login(data)

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, db_session, test_user):
        """Test login with inactive user."""
        service = AuthService(db_session)

        # Make user inactive
        test_user.is_active = False
        db_session.add(test_user)
        await db_session.commit()

        data = UserLoginRequest(email=test_user.email, password="Test1234!")

        with pytest.raises(UnauthorizedException):
            await service.login(data)

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, db_session, test_user):
        """Test token refresh."""
        service = AuthService(db_session)

        # Create refresh token
        refresh_token = create_refresh_token({"sub": test_user.id})

        # Refresh access token
        result = await service.refresh_access_token(refresh_token)

        assert result.access_token is not None
        assert result.refresh_token == refresh_token  # Same refresh token returned
        assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, db_session):
        """Test refresh with invalid token."""
        service = AuthService(db_session)

        with pytest.raises(UnauthorizedException):
            await service.refresh_access_token("invalid.token.here")

    @pytest.mark.asyncio
    async def test_verify_email(self, db_session, test_user):
        """Test email verification."""
        service = AuthService(db_session)

        # Mark as unverified first
        test_user.is_email_verified = False
        # Set verification token
        token = create_email_verification_token(test_user.email)
        test_user.email_verification_token = token
        test_user.email_verification_token_expires = datetime.now(UTC) + timedelta(hours=24)
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)

        # Verify
        user = await service.verify_email(token)

        assert user.is_email_verified is True

        # Check user is now verified
        user_repo = UserRepository(db_session)
        verified_user = await user_repo.get_by_email(test_user.email)
        assert verified_user.is_email_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, db_session):
        """Test email verification with invalid token."""
        service = AuthService(db_session)

        with pytest.raises(ValidationException):
            await service.verify_email("invalid-token")

    @pytest.mark.asyncio
    async def test_verify_email_already_verified(self, db_session, test_user):
        """Test email verification when already verified."""
        service = AuthService(db_session)

        # Ensure user is verified
        test_user.is_email_verified = True
        db_session.add(test_user)
        await db_session.commit()

        # Create verification token
        token = create_email_verification_token(test_user.email)

        # Verify (should return user without error)
        user = await service.verify_email(token)
        assert user.is_email_verified is True

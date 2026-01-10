from datetime import timedelta

import pytest
from jose import JWTError

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


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$argon2")

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """Test decoding valid token."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded["sub"] == "user@example.com"
        assert decoded["user_id"] == "123"
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_decode_expired_token(self):
        """Test decoding expired token."""
        data = {"sub": "user@example.com"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(JWTError):
            decode_token(token)

    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        with pytest.raises(JWTError):
            decode_token("invalid.token.here")


class TestEmailVerification:
    """Test email verification tokens."""

    def test_create_email_verification_token(self):
        """Test creating email verification token."""
        email = "user@example.com"
        token = create_email_verification_token(email)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_email_token_valid(self):
        """Test verifying valid email token."""
        email = "user@example.com"
        token = create_email_verification_token(email)

        verified_email = verify_email_token(token)

        assert verified_email == email

    def test_verify_email_token_invalid(self):
        """Test verifying invalid email token."""
        verified_email = verify_email_token("invalid.token")

        assert verified_email is None

    def test_verify_wrong_token_type(self):
        """Test that access token doesn't work for email verification."""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)

        verified_email = verify_email_token(token)

        assert verified_email is None


class TestPasswordResetToken:
    """Test password reset tokens."""

    def test_create_password_reset_token(self):
        """Test creating password reset token."""
        email = "user@example.com"
        token = create_password_reset_token(email)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_password_reset_token_valid(self):
        """Test verifying valid password reset token."""
        email = "user@example.com"
        token = create_password_reset_token(email)

        verified_email = verify_password_reset_token(token)

        assert verified_email == email

    def test_verify_password_reset_token_invalid(self):
        """Test verifying invalid password reset token."""
        verified_email = verify_password_reset_token("invalid.token")

        assert verified_email is None

    def test_verify_wrong_token_type_for_password_reset(self):
        """Test that access token doesn't work for password reset."""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)

        verified_email = verify_password_reset_token(token)

        assert verified_email is None

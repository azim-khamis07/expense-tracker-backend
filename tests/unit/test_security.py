"""Unit tests for security module."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_email_token,
    verify_password,
    verify_password_reset_token,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed)
        assert not verify_password("WrongPass123!", hashed)

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "SamePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Argon2 includes salt, so hashes should be different
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_empty_password(self):
        """Test that empty password is handled."""
        password = ""
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_unicode_password(self):
        """Test password with unicode characters."""
        password = "Pässwörd123! 🔒"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
        assert not verify_password("Password123!", hashed)


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_and_decode_access_token(self):
        """Test access token creation and decoding."""
        user_id = "test-user-123"
        data = {"sub": user_id, "type": "access"}
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiration."""
        user_id = "test-user-456"
        data = {"sub": user_id, "type": "access"}
        custom_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta=custom_delta)

        payload = decode_token(token)
        assert payload["sub"] == user_id
        # Verify expiration is approximately 2 hours from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_exp = datetime.now(UTC) + custom_delta
        # Allow 5 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    def test_expired_token(self):
        """Test expired token raises exception."""
        from jose import JWTError

        user_id = "test-user-789"
        data = {"sub": user_id, "type": "access"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(JWTError):
            decode_token(token)

    def test_invalid_token(self):
        """Test invalid token raises exception."""
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("invalid.token.here")

    def test_malformed_token(self):
        """Test malformed token raises exception."""
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("not.a.valid.jwt.token")

    def test_token_with_wrong_secret(self):
        """Test token signed with wrong secret fails."""
        from jose import JWTError, jwt

        from app.core.config import settings

        # Create token with wrong secret
        payload = {
            "sub": "user-123",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        wrong_token = jwt.encode(payload, "wrong-secret-key", algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(JWTError):
            decode_token(wrong_token)


class TestEmailVerificationToken:
    """Test email verification tokens."""

    def test_create_and_verify_email_token(self):
        """Test email verification token creation and verification."""
        email = "test@example.com"
        token = create_email_verification_token(email)

        verified_email = verify_email_token(token)
        assert verified_email == email

    def test_expired_email_token(self):
        """Test expired email token returns None."""
        from jose import jwt

        from app.core.config import settings

        email = "test@example.com"
        # Create expired token
        expired_payload = {
            "sub": email,
            "type": "email_verification",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        verified_email = verify_email_token(expired_token)
        assert verified_email is None

    def test_invalid_email_token(self):
        """Test invalid email token returns None."""
        invalid_token = "invalid-token"

        verified_email = verify_email_token(invalid_token)
        assert verified_email is None

    def test_wrong_token_type(self):
        """Test token with wrong type returns None."""
        from jose import jwt

        from app.core.config import settings

        email = "test@example.com"
        # Create token with wrong type
        wrong_payload = {
            "sub": email,
            "type": "access",  # Wrong type
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        wrong_token = jwt.encode(
            wrong_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        verified_email = verify_email_token(wrong_token)
        assert verified_email is None


class TestPasswordResetToken:
    """Test password reset tokens."""

    def test_create_and_verify_password_reset_token(self):
        """Test password reset token creation and verification."""
        email = "reset@example.com"
        token = create_password_reset_token(email)

        verified_email = verify_password_reset_token(token)
        assert verified_email == email

    def test_expired_password_reset_token(self):
        """Test expired password reset token returns None."""
        from jose import jwt

        from app.core.config import settings

        email = "reset@example.com"
        # Create expired token
        expired_payload = {
            "sub": email,
            "type": "password_reset",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        verified_email = verify_password_reset_token(expired_token)
        assert verified_email is None

    def test_invalid_password_reset_token(self):
        """Test invalid password reset token returns None."""
        invalid_token = "invalid-reset-token"

        verified_email = verify_password_reset_token(invalid_token)
        assert verified_email is None

    def test_wrong_token_type(self):
        """Test token with wrong type returns None."""
        from jose import jwt

        from app.core.config import settings

        email = "reset@example.com"
        # Create token with wrong type
        wrong_payload = {
            "sub": email,
            "type": "access",  # Wrong type
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        wrong_token = jwt.encode(
            wrong_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        verified_email = verify_password_reset_token(wrong_token)
        assert verified_email is None

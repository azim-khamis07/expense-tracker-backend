from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context (using Argon2 - more secure than bcrypt)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored password hash

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Dictionary of claims to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create JWT refresh token with longer expiration.

    Args:
        data: Dictionary of claims to encode in token

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Dictionary of decoded claims

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}") from e


def create_email_verification_token(email: str) -> str:
    """
    Create token for email verification.

    Args:
        email: User's email address

    Returns:
        Encoded token string
    """
    expire = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
    to_encode = {"sub": email, "exp": expire, "type": "email_verification"}

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """
    Create token for password reset.

    Args:
        email: User's email address

    Returns:
        Encoded token string
    """
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    to_encode = {"sub": email, "exp": expire, "type": "password_reset"}

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_email_token(token: str) -> str | None:
    """
    Verify email verification token and extract email.

    Args:
        token: Email verification token

    Returns:
        Email address if valid, None if invalid
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "email_verification":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def verify_password_reset_token(token: str) -> str | None:
    """
    Verify password reset token and extract email.

    Args:
        token: Password reset token

    Returns:
        Email address if valid, None if invalid
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None

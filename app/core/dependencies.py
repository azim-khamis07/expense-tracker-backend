import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}

    Raises:
        UnauthorizedException: If token is invalid, expired, or user not found
    """
    token = credentials.credentials

    try:
        # Decode JWT token
        payload = decode_token(token)

        # Verify token type
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")

        # Extract user ID from "sub" claim (standard JWT subject field)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Invalid token payload: missing user ID")

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise UnauthorizedException("Could not validate credentials") from e

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise UnauthorizedException("User not found")

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user_id}")
        raise UnauthorizedException("User account is inactive")

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current user with verified email.

    This dependency requires the user to have a verified email address.
    Use this for endpoints that require email verification.

    Usage:
        @app.get("/verified-only")
        async def verified_route(user: User = Depends(get_current_verified_user)):
            return {"user_id": user.id}

    Raises:
        HTTPException: If user's email is not verified
    """
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )

    return current_user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Dependency to get current user if authenticated, None otherwise.

    Useful for endpoints that work differently for authenticated users.
    This will NOT raise an exception if no token is provided.

    Usage:
        @app.get("/optional-auth")
        async def optional_route(user: User | None = Depends(get_optional_current_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello guest"}

    Returns:
        User instance if authenticated and valid, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except Exception:
        # Silently return None for any authentication failure
        # This allows the endpoint to work for both authenticated and unauthenticated users
        return None

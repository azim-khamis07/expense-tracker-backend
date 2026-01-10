import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.rate_limit import rate_limit_by_ip
from app.db.session import get_db
from app.models.user import User
from app.modules.auth.schemas import (
    EmailVerificationRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.modules.auth.service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Background task to send email (placeholder)
async def send_verification_email(email: str, token: str) -> None:
    """Send verification email (implement with actual email service)."""
    logger.info(f"Sending verification email to {email}")
    # TODO: Implement actual email sending
    # For now, just log the token (in production, send via email service)
    logger.info(f"Verification token: {token}")
    logger.info(f"Verification URL: http://localhost:3000/verify-email?token={token}")


async def send_password_reset_email(email: str, token: str) -> None:
    """Send password reset email (placeholder)."""
    logger.info(f"Sending password reset email to {email}")
    # TODO: Implement actual email sending
    logger.info(f"Reset token: {token}")
    logger.info(f"Reset URL: http://localhost:3000/reset-password?token={token}")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password",
)
async def register(
    request: Request,
    data: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(
        rate_limit_by_ip(max_requests=10, window_seconds=60)
    ),  # 10 requests per minute
) -> UserResponse:
    """
    Register a new user.

    - **email**: Valid email address
    - **password**: Minimum 8 characters with uppercase, lowercase, and digit

    Returns user details and sends verification email.
    """
    service = AuthService(db)
    user, verification_token = await service.register(data)

    # Send verification email in background
    background_tasks.add_task(send_verification_email, user.email, verification_token)

    return UserResponse(
        id=user.id,
        email=user.email,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
    description="Authenticate user with email and password, returns JWT tokens",
)
async def login(
    request: Request,
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_by_ip(max_requests=5, window_seconds=60)),  # 5 requests per minute
) -> TokenResponse:
    """
    Login with email and password.

    Returns:
    - **access_token**: Short-lived JWT for API requests (15 minutes)
    - **refresh_token**: Long-lived JWT for refreshing access token (7 days)
    """
    service = AuthService(db)
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token.

    Provide a valid refresh token to get a new access token.
    """
    service = AuthService(db)
    return await service.refresh_access_token(data.refresh_token)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email",
    description="Verify user email with token from email",
)
async def verify_email(
    data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Verify email address.

    Provide the verification token received via email.
    """
    service = AuthService(db)
    await service.verify_email(data.token)

    return MessageResponse(message="Email verified successfully")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    description="Resend email verification token",
)
async def resend_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Resend email verification.

    Requires authentication. Sends new verification email.
    """
    service = AuthService(db)
    verification_token = await service.resend_verification_email(current_user.email)

    # Send verification email in background
    background_tasks.add_task(send_verification_email, current_user.email, verification_token)

    return MessageResponse(message="Verification email sent")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Request password reset link via email",
)
async def forgot_password(
    request: Request,
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_by_ip(max_requests=5, window_seconds=3600)),  # 5 requests per hour
) -> MessageResponse:
    """
    Request password reset.

    Sends password reset email if account exists.
    Always returns success (don't reveal if email exists).
    """
    service = AuthService(db)
    reset_token = await service.request_password_reset(data.email)

    # Send reset email if user exists
    if reset_token:
        background_tasks.add_task(send_password_reset_email, data.email, reset_token)

    # Always return success (security: don't reveal if email exists)
    return MessageResponse(
        message="If your email is registered, you will receive a password reset link"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description="Reset password with token from email",
)
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Reset password.

    Provide the reset token from email and new password.
    """
    service = AuthService(db)
    await service.reset_password(data.token, data.new_password)

    return MessageResponse(message="Password reset successfully")


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Logout user (client should discard tokens)",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Logout.

    Currently stateless (client discards tokens).
    In production, you might want to blacklist tokens in Redis.
    """
    logger.info(f"User logged out: {current_user.email}")

    # TODO: Optionally blacklist refresh token in Redis
    # await redis_client.set(f"blacklist:{refresh_token}", "1", ex=604800)

    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get currently authenticated user details",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user profile.

    Requires authentication.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_email_verified=current_user.is_email_verified,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
    )

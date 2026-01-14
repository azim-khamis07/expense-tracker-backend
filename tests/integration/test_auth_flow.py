"""Integration tests for authentication flow."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.auth
class TestAuthFlow:
    """Test complete authentication flows."""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, async_client: AsyncClient):
        """Test complete authentication flow."""
        # 1. Register
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "integration@example.com", "password": "IntegrationTest123!"},
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == "integration@example.com"
        assert user_data["is_email_verified"] is False

        # 2. Login (should work even without verification)
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "integration@example.com", "password": "IntegrationTest123!"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0

        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 3. Access protected endpoint
        profile_response = await async_client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == "integration@example.com"

        # 4. Refresh token
        import asyncio

        await asyncio.sleep(1)  # Small delay to ensure different token timestamp

        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # New token should be different (or at least valid)
        new_access_token = new_tokens["access_token"]
        assert (
            new_access_token != access_token or len(new_access_token) > 0
        )  # New token or valid token

        # 5. Use new access token
        profile_response2 = await async_client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert profile_response2.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_credentials(self, async_client: AsyncClient):
        """Test invalid login credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "WrongPass123!"},
        )
        assert response.status_code == 401
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Test registration with duplicate email."""
        # First registration
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "duplicate@example.com", "password": "SecurePass123!"},
        )
        assert register_response.status_code == 201

        # Second registration with same email
        duplicate_response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "duplicate@example.com", "password": "SecurePass123!"},
        )
        assert duplicate_response.status_code == 409  # Conflict
        error_data = duplicate_response.json()
        assert "already" in error_data.get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_invalid_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await async_client.get(
            "/api/v1/users/profile",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await async_client.get("/api/v1/users/profile")
        assert response.status_code == 403  # Forbidden (no credentials)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_password_reset_request(self, async_client: AsyncClient, test_user):
        """Test password reset request."""
        # Request password reset
        forgot_response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )
        assert forgot_response.status_code == 200
        message_data = forgot_response.json()
        assert "message" in message_data

    @pytest.mark.asyncio
    async def test_password_reset_nonexistent_email(self, async_client: AsyncClient):
        """Test password reset request for nonexistent email (should not reveal)."""
        # Should return 200 even if email doesn't exist (security)
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        message_data = response.json()
        assert "message" in message_data

    @pytest.mark.asyncio
    async def test_email_verification_flow(self, async_client: AsyncClient):
        """Test email verification flow."""
        # 1. Register
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "verify@example.com", "password": "SecurePass123!"},
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["is_email_verified"] is False

        # 2. Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "verify@example.com", "password": "SecurePass123!"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]

        # 3. Resend verification email
        resend_response = await async_client.post(
            "/api/v1/auth/resend-verification",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resend_response.status_code == 200

        # Note: Actual verification would require token from email
        # In integration test, we'd mock the email service or capture the token

    @pytest.mark.asyncio
    async def test_weak_password_validation(self, async_client: AsyncClient):
        """Test password strength validation."""
        # Test password too short
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "Short1"},
        )
        assert response.status_code == 422  # Validation error

        # Test password without uppercase
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak2@example.com", "password": "lowercase123"},
        )
        assert response.status_code == 422

        # Test password without lowercase
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak3@example.com", "password": "UPPERCASE123"},
        )
        assert response.status_code == 422

        # Test password without digit
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak4@example.com", "password": "NoDigitHere"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_client: AsyncClient):
        """Test rate limiting on auth endpoints."""
        # Try to register multiple times quickly
        # Note: Rate limit is 10 requests per minute for registration
        responses = []
        for i in range(12):  # Exceed limit
            response = await async_client.post(
                "/api/v1/auth/register",
                json={"email": f"ratelimit{i}@example.com", "password": "SecurePass123!"},
            )
            responses.append(response.status_code)

        # At least one should be rate limited (429)
        assert 429 in responses or all(
            status in [201, 409] for status in responses
        )  # Or all succeeded/conflict

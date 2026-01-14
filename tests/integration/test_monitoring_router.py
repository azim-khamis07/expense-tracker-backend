"""Integration tests for monitoring router."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestMonitoringRouter:
    """Test monitoring router endpoints."""

    async def test_health_check_basic(self, async_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_detailed_health_check_success(self, async_client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await async_client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "s3" in data["services"]
        assert data["services"]["database"]["status"] in ["healthy", "unhealthy"]
        assert data["services"]["redis"]["status"] in ["healthy", "unhealthy"]

    async def test_metrics_endpoint(self, async_client: AsyncClient):
        """Test system metrics endpoint (JSON format)."""
        response = await async_client.get("/api/v1/metrics/system")

        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "database" in data
        # System metrics should have CPU, memory, disk
        if "error" not in data["system"]:
            assert "cpu_percent" in data["system"] or "memory_percent" in data["system"]
        # Database stats may have counts or error
        assert isinstance(data["database"], dict)
        assert "system" in data
        assert "database" in data
        # System metrics should have CPU, memory, disk
        if "error" not in data["system"]:
            assert "cpu_percent" in data["system"] or "memory_percent" in data["system"]
        # Database stats may have counts or error
        assert isinstance(data["database"], dict)

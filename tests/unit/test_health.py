"""Unit tests for health check functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.health import (
    check_database_health,
    check_redis_health,
    check_s3_health,
    get_system_metrics,
)


class TestDatabaseHealth:
    """Test database health check."""

    @pytest.mark.asyncio
    async def test_database_health_success(self):
        """Test successful database health check."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        result = await check_database_health(mock_db)

        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert result["response_time_ms"] >= 0
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_health_failure(self):
        """Test database health check failure."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("Connection failed")

        result = await check_database_health(mock_db)

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "Connection failed" in result["error"]


class TestRedisHealth:
    """Test Redis health check."""

    @pytest.mark.asyncio
    async def test_redis_health_success_with_redis_client(self):
        """Test successful Redis health check with RedisClient wrapper."""
        mock_redis_wrapper = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_wrapper.redis = mock_redis_client

        result = await check_redis_health(mock_redis_wrapper)

        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert result["response_time_ms"] >= 0
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_health_success_direct_client(self):
        """Test successful Redis health check with direct client."""
        # Create a mock that doesn't have .redis attribute (direct client)
        mock_redis_client = AsyncMock()
        # Remove .redis attribute if it exists
        if hasattr(mock_redis_client, "redis"):
            delattr(mock_redis_client, "redis")
        mock_redis_client.ping = AsyncMock(return_value=True)

        result = await check_redis_health(mock_redis_client)

        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        # ping is called on the client directly (not through .redis attribute)
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_health_failure(self):
        """Test Redis health check failure."""
        mock_redis_wrapper = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
        mock_redis_wrapper.redis = mock_redis_client

        result = await check_redis_health(mock_redis_wrapper)

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "Connection failed" in result["error"]


class TestS3Health:
    """Test S3 health check."""

    @pytest.mark.asyncio
    async def test_s3_health_success(self):
        """Test successful S3 health check."""
        mock_settings = MagicMock()
        mock_settings.S3_ENDPOINT_URL = "http://localhost:9000"
        mock_settings.S3_ACCESS_KEY_ID = "test_key"

        mock_s3_client = MagicMock()
        mock_s3_client.bucket_name = "test-bucket"
        mock_s3_client.s3_client.list_objects_v2 = MagicMock(return_value={})

        with (
            patch("app.core.config.settings", mock_settings),
            patch("app.infra.s3.S3Client", return_value=mock_s3_client),
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = AsyncMock(return_value={})
            mock_loop.return_value = mock_loop_instance

            result = await check_s3_health()

            assert result["status"] == "healthy"
            assert "response_time_ms" in result
            assert result["response_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_s3_health_not_configured(self):
        """Test S3 health check when not configured."""
        mock_settings = MagicMock()
        mock_settings.S3_ENDPOINT_URL = ""
        mock_settings.S3_ACCESS_KEY_ID = ""

        with patch("app.core.config.settings", mock_settings):
            result = await check_s3_health()

            assert result["status"] == "not_configured"
            assert "message" in result
            assert "not configured" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_s3_health_failure(self):
        """Test S3 health check failure."""
        mock_settings = MagicMock()
        mock_settings.S3_ENDPOINT_URL = "http://localhost:9000"
        mock_settings.S3_ACCESS_KEY_ID = "test_key"

        mock_s3_client = MagicMock()
        mock_s3_client.bucket_name = "test-bucket"
        mock_s3_client.s3_client.list_objects_v2 = MagicMock(
            side_effect=Exception("Connection failed")
        )

        with (
            patch("app.core.config.settings", mock_settings),
            patch("app.infra.s3.S3Client", return_value=mock_s3_client),
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            mock_loop.return_value = mock_loop_instance

            result = await check_s3_health()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Connection failed" in result["error"]


class TestSystemMetrics:
    """Test system metrics."""

    @pytest.mark.asyncio
    async def test_system_metrics_success(self):
        """Test successful system metrics retrieval."""
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = MagicMock(percent=45.2)
        mock_psutil.disk_usage.return_value = MagicMock(percent=60.1)

        # Patch where psutil is imported (inside the function)
        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "psutil":
                    return mock_psutil
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            result = await get_system_metrics()

            assert result["cpu_percent"] == 25.5
            assert result["memory_percent"] == 45.2
            assert result["disk_percent"] == 60.1

    @pytest.mark.asyncio
    async def test_system_metrics_psutil_not_installed(self):
        """Test system metrics when psutil is not installed."""
        # Patch import to raise ImportError for psutil
        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "psutil":
                    raise ImportError("No module named psutil")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            result = await get_system_metrics()

            assert result["cpu_percent"] is None
            assert result["memory_percent"] is None
            assert result["disk_percent"] is None
            assert "error" in result
            assert "psutil not installed" in result["error"]

    @pytest.mark.asyncio
    async def test_system_metrics_error(self):
        """Test system metrics when psutil raises an error."""
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.side_effect = Exception("System error")

        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "psutil":
                    return mock_psutil
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            result = await get_system_metrics()

            assert result["cpu_percent"] is None
            assert result["memory_percent"] is None
            assert result["disk_percent"] is None
            assert "error" in result
            assert "System error" in result["error"]

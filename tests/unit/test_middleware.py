"""Unit tests for middleware."""

from fastapi.testclient import TestClient

from app.main import app


class TestRequestIDMiddleware:
    """Test RequestIDMiddleware."""

    def test_request_id_middleware_adds_id(self):
        """Test middleware adds request ID to request state."""
        client = TestClient(app)

        # Make a request
        response = client.get("/api/v1/health")

        # Check that X-Request-ID header is present
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None

    def test_request_id_middleware_unique_ids(self):
        """Test middleware generates unique request IDs."""
        client = TestClient(app)

        # Make multiple requests
        response1 = client.get("/api/v1/health")
        response2 = client.get("/api/v1/health")

        # Request IDs should be different
        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]

    def test_request_id_middleware_process_time(self):
        """Test middleware adds process time header."""
        client = TestClient(app)

        response = client.get("/api/v1/health")

        # Check that X-Process-Time header is present
        assert "X-Process-Time" in response.headers

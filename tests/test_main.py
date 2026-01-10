"""Tests for main FastAPI application."""


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data


def test_root_endpoint(client):
    """Test API root endpoint."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "v1"


def test_sample_user_data(sample_user_data):
    """Test sample user data fixture."""
    assert "email" in sample_user_data
    assert "password" in sample_user_data
    assert sample_user_data["email"] == "test@example.com"

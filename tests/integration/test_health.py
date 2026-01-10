def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["healthy", "degraded"]
    assert data["environment"] == "development"
    assert "request_id" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]


def test_api_root(client):
    """Test API root endpoint."""
    response = client.get("/api/v1/")

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert "version" in data
    assert data["version"] == "v1"

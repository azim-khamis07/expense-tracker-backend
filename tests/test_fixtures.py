"""Test fixtures to verify they work correctly."""

import pytest


def test_sample_user_data(sample_user_data):
    """Test sample_user_data fixture."""
    assert "email" in sample_user_data
    assert "password" in sample_user_data
    assert sample_user_data["email"] == "test@example.com"
    assert len(sample_user_data["password"]) > 0


def test_sample_category_data(sample_category_data):
    """Test sample_category_data fixture."""
    assert "name" in sample_category_data
    assert "type" in sample_category_data
    assert "description" in sample_category_data
    assert sample_category_data["type"] in ("expense", "income")


def test_sample_transaction_data(sample_transaction_data):
    """Test sample_transaction_data fixture."""
    assert "amount" in sample_transaction_data
    assert "currency" in sample_transaction_data
    assert "type" in sample_transaction_data
    assert "occurred_at" in sample_transaction_data
    assert "T" in sample_transaction_data["occurred_at"]  # ISO format


# Note: Direct async db_session testing has event loop issues with session-scoped fixtures.
# The db_session fixture is tested indirectly through client fixture tests.
# If you need to test db_session directly, use it within a test that also uses test_engine.


@pytest.mark.asyncio
async def test_client(client):
    """Test client fixture."""
    assert client is not None
    # Test that client works
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

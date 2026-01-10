"""Example test file to verify pytest configuration."""


def test_example():
    """Basic test to verify pytest is working."""
    assert 1 + 1 == 2


async def test_async_example():
    """Basic async test to verify pytest-asyncio is working."""
    result = await simple_async_function()
    assert result == "success"


async def simple_async_function():
    """Simple async function for testing."""
    return "success"

import asyncio
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("expense_tracker", "expense_tracker_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback after each test


@pytest.fixture
def client(test_engine):
    """Create test client with database override.

    Creates a new test database session for each test request.
    This avoids async fixture dependency issues with synchronous TestClient.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {"email": "test@example.com", "password": "SecurePass123!"}


@pytest.fixture
def sample_category_data():
    """Sample category data for testing."""
    return {
        "name": "Groceries",
        "type": "expense",
        "description": "Food and household items",
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    from app.utils.datetime_utils import utcnow

    return {
        "amount": "100.50",
        "currency": "USD",
        "type": "expense",
        "description": "Grocery shopping",
        "occurred_at": utcnow().isoformat(),
    }

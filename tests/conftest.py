"""Pytest configuration and fixtures."""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User

# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("expense_tracker", "expense_tracker_test")

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

fake = Faker()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Create test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database override."""
    from httpx import ASGITransport

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        password_hash=hash_password("Test1234!"),
        is_email_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(async_client: AsyncClient, test_user: User) -> str:
    """Get authentication token."""
    # First register/login the user
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "Test1234!"},
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    # If login fails, try registration
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": test_user.email, "password": "Test1234!"},
    )
    if response.status_code == 201:
        # Then login
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "Test1234!"},
        )
        return response.json()["access_token"]
    raise Exception("Failed to get auth token")


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Get authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def test_categories(db_session: AsyncSession, test_user: User) -> list[Category]:
    """Create test categories."""
    categories = [
        Category(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            name="Food",
            type="expense",
            description="Food and groceries",
        ),
        Category(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            name="Transport",
            type="expense",
            description="Transportation expenses",
        ),
        Category(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            name="Salary",
            type="income",
            description="Monthly salary",
        ),
    ]
    for cat in categories:
        db_session.add(cat)
    await db_session.commit()
    for cat in categories:
        await db_session.refresh(cat)
    return categories


@pytest_asyncio.fixture
async def test_transactions(
    db_session: AsyncSession,
    test_user: User,
    test_categories: list[Category],
) -> list[Transaction]:
    """Create test transactions."""
    transactions = []
    base_date = datetime.now(UTC) - timedelta(days=30)

    # Create expense transactions
    for i in range(50):
        trans = Transaction(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            category_id=test_categories[i % 2].id,  # Alternate expense categories
            type="expense",
            amount=fake.pydecimal(left_digits=3, right_digits=2, positive=True),
            currency="USD",
            description=fake.sentence(),
            occurred_at=base_date + timedelta(days=i % 30),
        )
        db_session.add(trans)
        transactions.append(trans)

    # Add some income transactions
    for i in range(10):
        trans = Transaction(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            category_id=test_categories[2].id,  # Salary category
            type="income",
            amount=5000.00,
            currency="USD",
            description="Monthly salary",
            occurred_at=base_date + timedelta(days=i * 3),
        )
        db_session.add(trans)
        transactions.append(trans)

    await db_session.commit()
    for trans in transactions:
        await db_session.refresh(trans)

    return transactions


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {"email": "test@example.com", "password": "SecurePass123!"}


@pytest.fixture
def sample_category_data() -> dict[str, Any]:
    """Sample category data for testing."""
    return {
        "name": "Groceries",
        "type": "expense",
        "description": "Food and household items",
    }


@pytest.fixture
def sample_transaction_data() -> dict[str, Any]:
    """Sample transaction creation data.

    Note: category_id must be provided when creating a transaction.
    This fixture provides a placeholder that should be replaced with an actual category ID.
    """
    return {
        "type": "expense",
        "amount": 50.00,
        "currency": "USD",
        "description": "Test expense",
        "occurred_at": datetime.now(UTC).isoformat(),
        "category_id": "REQUIRED",  # Must be replaced with actual category ID
        "tag_ids": [],
    }

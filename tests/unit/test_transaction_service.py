from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.security import hash_password
from app.models.user import User
from app.modules.categories.schemas import CategoryCreate
from app.modules.categories.service import CategoryService
from app.modules.tags.schemas import TagCreate
from app.modules.tags.service import TagService
from app.modules.transactions.schemas import TransactionCreate, TransactionListFilter
from app.modules.transactions.service import TransactionService


@pytest.mark.asyncio
class TestTransactionService:
    """Test transaction service."""

    async def test_create_transaction(self, db_session, sample_user_data):
        """Test creating a transaction."""
        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create category
        cat_service = CategoryService(db_session)
        category = await cat_service.create_category(
            user.id, CategoryCreate(name="Test", type="expense", description="Test category")
        )

        # Create transaction
        service = TransactionService(db_session)
        transaction = await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("100.50"),
                currency="USD",
                type="expense",
                category_id=category.id,
                description="Test transaction",
                occurred_at=datetime.now(UTC),
            ),
        )

        assert transaction.amount == Decimal("100.50")
        assert transaction.type == "expense"
        assert transaction.currency == "USD"
        assert transaction.category_id == category.id
        assert transaction.category_name == "Test"
        assert transaction.description == "Test transaction"

    async def test_create_transaction_with_tags(self, db_session, sample_user_data):
        """Test creating a transaction with tags."""
        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create category
        cat_service = CategoryService(db_session)
        category = await cat_service.create_category(
            user.id, CategoryCreate(name="Test", type="expense", description="Test category")
        )

        # Create tags
        tag_service = TagService(db_session)
        tag1 = await tag_service.create_tag(user.id, TagCreate(name="urgent", color="#FF0000"))
        tag2 = await tag_service.create_tag(user.id, TagCreate(name="personal", color="#00FF00"))

        # Create transaction with tags
        service = TransactionService(db_session)
        transaction = await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("100.50"),
                currency="USD",
                type="expense",
                category_id=category.id,
                description="Test transaction",
                occurred_at=datetime.now(UTC),
                tag_ids=[tag1.id, tag2.id],
            ),
        )

        assert transaction.amount == Decimal("100.50")
        assert len(transaction.tags) == 2
        assert {tag["id"] for tag in transaction.tags} == {tag1.id, tag2.id}

    async def test_list_transactions_with_filters(self, db_session, sample_user_data):
        """Test listing transactions with filters."""
        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        service = TransactionService(db_session)

        # Create test transactions
        for i in range(5):
            await service.create_transaction(
                user.id,
                TransactionCreate(
                    amount=Decimal(str(100 + i * 10)),
                    currency="USD",
                    type="expense" if i % 2 == 0 else "income",
                    description=f"Transaction {i}",
                    occurred_at=datetime.now(UTC) - timedelta(days=i),
                ),
            )

        # List all
        filters = TransactionListFilter(limit=10)
        result = await service.list_transactions(user.id, filters)

        assert len(result.data) == 5
        assert result.has_more is False

        # Filter by type
        filters = TransactionListFilter(type="expense", limit=10)
        result = await service.list_transactions(user.id, filters)

        assert len(result.data) == 3  # 0, 2, 4 are expenses
        assert all(t.type == "expense" for t in result.data)

        # Filter by amount range
        filters = TransactionListFilter(
            min_amount=Decimal("110"), max_amount=Decimal("130"), limit=10
        )
        result = await service.list_transactions(user.id, filters)

        assert len(result.data) == 3  # 110, 120, 130
        assert all(Decimal("110") <= t.amount <= Decimal("130") for t in result.data)

    async def test_get_transaction(self, db_session, sample_user_data):
        """Test getting a transaction by ID."""
        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("100.50"),
                currency="USD",
                type="expense",
                description="Test transaction",
                occurred_at=datetime.now(UTC),
            ),
        )

        # Get transaction
        retrieved = await service.get_transaction(created.id, user.id)

        assert retrieved.id == created.id
        assert retrieved.amount == Decimal("100.50")
        assert retrieved.description == "Test transaction"

    async def test_update_transaction(self, db_session, sample_user_data):
        """Test updating a transaction."""
        from app.modules.transactions.schemas import TransactionUpdate

        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create category
        cat_service = CategoryService(db_session)
        category = await cat_service.create_category(
            user.id, CategoryCreate(name="Test", type="expense", description="Test category")
        )

        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("100.50"),
                currency="USD",
                type="expense",
                category_id=category.id,
                description="Original description",
                occurred_at=datetime.now(UTC),
            ),
        )

        # Update transaction
        updated = await service.update_transaction(
            created.id,
            user.id,
            TransactionUpdate(
                amount=Decimal("150.00"),
                description="Updated description",
            ),
        )

        assert updated.id == created.id
        assert updated.amount == Decimal("150.00")
        assert updated.description == "Updated description"
        assert updated.category_id == category.id  # Unchanged

    async def test_delete_transaction(self, db_session, sample_user_data):
        """Test soft deleting a transaction."""
        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("100.50"),
                currency="USD",
                type="expense",
                description="Test transaction",
                occurred_at=datetime.now(UTC),
            ),
        )

        # Delete transaction
        await service.delete_transaction(created.id, user.id)

        # Verify transaction is not in list (soft delete)
        filters = TransactionListFilter(limit=10)
        result = await service.list_transactions(user.id, filters)

        assert len(result.data) == 0

        # Verify get_transaction raises NotFoundException
        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await service.get_transaction(created.id, user.id)

    async def test_get_stats(self, db_session, sample_user_data):
        """Test getting transaction statistics."""
        # Create user
        user = User(
            email=sample_user_data["email"],
            password_hash=hash_password(sample_user_data["password"]),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        service = TransactionService(db_session)

        # Create test transactions
        await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("100.00"),
                currency="USD",
                type="expense",
                description="Expense 1",
                occurred_at=datetime.now(UTC),
            ),
        )

        await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("50.00"),
                currency="USD",
                type="expense",
                description="Expense 2",
                occurred_at=datetime.now(UTC),
            ),
        )

        await service.create_transaction(
            user.id,
            TransactionCreate(
                amount=Decimal("500.00"),
                currency="USD",
                type="income",
                description="Income 1",
                occurred_at=datetime.now(UTC),
            ),
        )

        # Get stats
        stats = await service.get_stats(user.id)

        assert stats.total_expense == Decimal("150.00")
        assert stats.total_income == Decimal("500.00")
        assert stats.net == Decimal("350.00")
        assert stats.transaction_count == 3
        # Average is (150 + 500) / 3 = 216.66666..., allow for precision differences
        expected_avg = (stats.total_expense + stats.total_income) / stats.transaction_count
        assert abs(stats.average_transaction - expected_avg) < Decimal("0.01")

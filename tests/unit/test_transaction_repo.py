"""Unit tests for transaction repository."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.transaction import Transaction
from app.modules.transactions.repo import TransactionRepository


@pytest.mark.unit
@pytest.mark.transactions
class TestTransactionRepository:
    """Test transaction repository methods."""

    @pytest.mark.asyncio
    async def test_create_transaction(self, db_session, test_user, test_categories):
        """Test transaction creation."""
        repo = TransactionRepository(db_session)

        trans_data = Transaction(
            user_id=test_user.id,
            category_id=test_categories[0].id,
            type="expense",
            amount=Decimal("100.50"),
            currency="USD",
            description="Test transaction",
            occurred_at=datetime.now(UTC),
        )
        trans = await repo.create(trans_data)

        assert trans.id is not None
        assert trans.amount == Decimal("100.50")
        assert trans.type == "expense"
        assert trans.user_id == test_user.id
        assert trans.category_id == test_categories[0].id
        assert trans.deleted_at is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session, test_user, test_categories):
        """Test getting transaction by ID."""
        repo = TransactionRepository(db_session)

        trans_data = Transaction(
            user_id=test_user.id,
            category_id=test_categories[0].id,
            type="expense",
            amount=Decimal("50.00"),
            currency="USD",
            description="Get by ID test",
            occurred_at=datetime.now(UTC),
        )
        created = await repo.create(trans_data)

        fetched = await repo.get_by_id(created.id, test_user.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.amount == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_soft_delete(self, db_session, test_user, test_categories):
        """Test soft delete functionality."""
        repo = TransactionRepository(db_session)

        trans_data = Transaction(
            user_id=test_user.id,
            category_id=test_categories[0].id,
            type="expense",
            amount=Decimal("50.00"),
            currency="USD",
            description="To be deleted",
            occurred_at=datetime.now(UTC),
        )
        created = await repo.create(trans_data)
        await db_session.commit()

        # Soft delete (takes Transaction object)
        await repo.soft_delete(created)
        await db_session.commit()

        # Should not appear in regular queries
        fetched = await repo.get_by_id(created.id, test_user.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_list_with_date_filter(self, db_session, test_user, test_transactions):
        """Test listing with date filters."""
        repo = TransactionRepository(db_session)
        await db_session.commit()  # Ensure transactions are committed

        start_date = datetime.now(UTC) - timedelta(days=15)
        end_date = datetime.now(UTC) - timedelta(days=5)

        transactions, cursor, has_more = await repo.list_with_filters(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date,
            limit=100,
        )

        # All transactions should be within date range
        for trans in transactions:
            assert start_date <= trans.occurred_at <= end_date

    @pytest.mark.asyncio
    async def test_list_with_category_filter(
        self, db_session, test_user, test_transactions, test_categories
    ):
        """Test listing with category filter."""
        repo = TransactionRepository(db_session)
        await db_session.commit()  # Ensure transactions are committed

        category_id = test_categories[0].id

        transactions, cursor, has_more = await repo.list_with_filters(
            user_id=test_user.id,
            category_id=category_id,
            limit=100,
        )

        # All transactions should have the specified category
        for trans in transactions:
            assert trans.category_id == category_id

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, db_session, test_user, test_transactions):
        """Test listing with transaction type filter."""
        repo = TransactionRepository(db_session)
        await db_session.commit()  # Ensure transactions are committed

        transactions, cursor, has_more = await repo.list_with_filters(
            user_id=test_user.id,
            type="income",
            limit=100,
        )

        # All transactions should be income type
        for trans in transactions:
            assert trans.type == "income"

    @pytest.mark.asyncio
    async def test_list_with_amount_range(self, db_session, test_user, test_transactions):
        """Test listing with amount range."""
        repo = TransactionRepository(db_session)
        await db_session.commit()  # Ensure transactions are committed

        transactions, cursor, has_more = await repo.list_with_filters(
            user_id=test_user.id,
            min_amount=Decimal("1000.00"),
            max_amount=Decimal("6000.00"),
            limit=100,
        )

        # All transactions should be within amount range
        for trans in transactions:
            assert Decimal("1000.00") <= trans.amount <= Decimal("6000.00")

    @pytest.mark.asyncio
    async def test_get_stats(self, db_session, test_user, test_transactions):
        """Test statistics calculation."""
        repo = TransactionRepository(db_session)
        await db_session.commit()  # Ensure transactions are committed

        stats = await repo.get_stats(
            user_id=test_user.id,
            start_date=datetime.now(UTC) - timedelta(days=30),
            end_date=datetime.now(UTC),
        )

        assert "total_income" in stats
        assert "total_expense" in stats  # Fixed: key is "total_expense" not "total_expenses"
        assert "net" in stats
        assert "transaction_count" in stats
        assert stats["transaction_count"] > 0
        assert stats["net"] == stats["total_income"] - stats["total_expense"]

    @pytest.mark.asyncio
    async def test_cursor_pagination(self, db_session, test_user, test_transactions):
        """Test cursor-based pagination."""
        repo = TransactionRepository(db_session)
        await db_session.commit()  # Ensure transactions are committed

        # First page
        page1, cursor1, has_more1 = await repo.list_with_filters(
            user_id=test_user.id,
            limit=10,
        )

        assert len(page1) <= 10
        if cursor1 is not None and has_more1:
            # Second page
            page2, cursor2, has_more2 = await repo.list_with_filters(
                user_id=test_user.id,
                cursor=cursor1,
                limit=10,
            )

            assert len(page2) > 0
            # Ensure no overlap
            page1_ids = {t.id for t in page1}
            page2_ids = {t.id for t in page2}
            assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_update_transaction(self, db_session, test_user, test_categories):
        """Test transaction update."""
        repo = TransactionRepository(db_session)

        trans_data = Transaction(
            user_id=test_user.id,
            category_id=test_categories[0].id,
            type="expense",
            amount=Decimal("100.00"),
            currency="USD",
            description="Original description",
            occurred_at=datetime.now(UTC),
        )
        created = await repo.create(trans_data)
        await db_session.commit()

        # Update
        created.description = "Updated description"
        created.amount = Decimal("150.00")
        updated = await repo.update(created)
        await db_session.commit()

        assert updated.description == "Updated description"
        assert updated.amount == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_session, test_user, test_categories):
        """Test that users can only access their own transactions."""
        import uuid

        from app.core.security import hash_password
        from app.models.user import User

        # Create another user
        other_user = User(
            id=str(uuid.uuid4()),
            email="other@example.com",
            password_hash=hash_password("Other123!"),
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        repo = TransactionRepository(db_session)

        # Create transaction for test_user
        trans_data = Transaction(
            user_id=test_user.id,
            category_id=test_categories[0].id,
            type="expense",
            amount=Decimal("100.00"),
            currency="USD",
            description="User transaction",
            occurred_at=datetime.now(UTC),
        )
        user_trans = await repo.create(trans_data)

        # Try to get it as other_user (should return None)
        fetched = await repo.get_by_id(user_trans.id, other_user.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_list_empty_result(self, db_session, test_user):
        """Test listing with no results."""
        repo = TransactionRepository(db_session)

        transactions, cursor, has_more = await repo.list_with_filters(
            user_id=test_user.id,
            start_date=datetime.now(UTC) + timedelta(days=365),  # Future date
            end_date=datetime.now(UTC) + timedelta(days=400),
            limit=100,
        )

        assert len(transactions) == 0
        assert cursor is None
        assert has_more is False

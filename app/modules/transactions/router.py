from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.transactions.schemas import (
    TransactionCreate,
    TransactionListFilter,
    TransactionPage,
    TransactionResponse,
    TransactionStats,
    TransactionUpdate,
)
from app.modules.transactions.service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transaction",
    description="Create a new expense or income transaction",
)
async def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new transaction.

    - **amount**: Positive decimal amount
    - **currency**: ISO 4217 code (default: USD)
    - **type**: 'expense' or 'income'
    - **category_id**: Optional category ID
    - **occurred_at**: When transaction occurred (ISO 8601)
    - **tag_ids**: Optional list of tag IDs
    """
    service = TransactionService(db)
    return await service.create_transaction(current_user.id, data)


@router.get(
    "",
    response_model=TransactionPage,
    summary="List transactions",
    description="List transactions with filters and cursor pagination",
)
async def list_transactions(
    start_date: datetime | None = Query(None, description="Start date (ISO 8601)"),
    end_date: datetime | None = Query(None, description="End date (ISO 8601)"),
    category_id: str | None = Query(None, description="Filter by category"),
    type: str | None = Query(None, description="Filter by type (expense/income)"),
    min_amount: Decimal | None = Query(None, ge=0, description="Minimum amount"),
    max_amount: Decimal | None = Query(None, ge=0, description="Maximum amount"),
    tag_ids: list[str] | None = Query(None, description="Filter by tags"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List transactions with advanced filtering.

    **Filters:**
    - Date range (start_date, end_date)
    - Category
    - Type (expense/income)
    - Amount range
    - Tags (transactions with ANY of the specified tags)

    **Pagination:**
    - Cursor-based (more efficient than offset)
    - Sorted by occurred_at DESC (newest first)
    """
    filters = TransactionListFilter(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        type=type,
        min_amount=min_amount,
        max_amount=max_amount,
        tag_ids=tag_ids,
        cursor=cursor,
        limit=limit,
    )

    service = TransactionService(db)
    return await service.list_transactions(current_user.id, filters)


@router.get(
    "/stats",
    response_model=TransactionStats,
    summary="Get transaction statistics",
    description="Get aggregated statistics for transactions",
)
async def get_transaction_stats(
    start_date: datetime | None = Query(None, description="Start date"),
    end_date: datetime | None = Query(None, description="End date"),
    category_id: str | None = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get transaction statistics.

    Returns:
    - Total income
    - Total expense
    - Net (income - expense)
    - Transaction count
    - Average transaction amount
    """
    service = TransactionService(db)
    return await service.get_stats(current_user.id, start_date, end_date, category_id)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction",
    description="Get transaction by ID",
)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction by ID."""
    service = TransactionService(db)
    return await service.get_transaction(transaction_id, current_user.id)


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction",
    description="Update transaction details",
)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update transaction.

    All fields are optional. Only provided fields will be updated.
    Use empty string for category_id to unset category.
    """
    service = TransactionService(db)
    return await service.update_transaction(transaction_id, current_user.id, data)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transaction",
    description="Soft delete transaction (can be restored)",
)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete transaction (soft delete).

    Transaction is marked as deleted but remains in database for audit.
    """
    service = TransactionService(db)
    await service.delete_transaction(transaction_id, current_user.id)
    return None

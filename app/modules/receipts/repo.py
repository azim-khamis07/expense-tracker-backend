import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt

logger = logging.getLogger(__name__)


class ReceiptRepository:
    """Repository for receipt database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, receipt_id: str) -> Receipt | None:
        """Get receipt by ID."""
        result = await self.db.execute(select(Receipt).where(Receipt.id == receipt_id))
        return result.scalar_one_or_none()

    async def get_by_transaction_id(self, transaction_id: str) -> Receipt | None:
        """Get receipt by transaction ID."""
        result = await self.db.execute(
            select(Receipt).where(Receipt.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def create(self, receipt: Receipt) -> Receipt:
        """Create new receipt."""
        self.db.add(receipt)
        await self.db.flush()
        await self.db.refresh(receipt)
        logger.info(f"Created receipt: {receipt.id} for transaction {receipt.transaction_id}")
        return receipt

    async def delete(self, receipt: Receipt) -> None:
        """Delete receipt."""
        await self.db.delete(receipt)
        await self.db.flush()
        logger.info(f"Deleted receipt: {receipt.id}")

    async def update_s3_key(self, receipt: Receipt, s3_key: str) -> Receipt:
        """Update S3 key for receipt."""
        receipt.s3_key = s3_key
        await self.db.flush()
        await self.db.refresh(receipt)
        return receipt

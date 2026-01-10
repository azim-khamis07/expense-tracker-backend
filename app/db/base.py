from sqlalchemy.orm import declarative_base

# Create declarative base for all models
Base = declarative_base()

# Import all models here for Alembic auto-detection
from app.models.category import Category
from app.models.receipt import Receipt
from app.models.report_job import ReportJob
from app.models.tag import Tag, transaction_tags
from app.models.transaction import Transaction
from app.models.user import User

# Export for easy imports
__all__ = [
    "Base",
    "User",
    "Category",
    "Tag",
    "transaction_tags",
    "Transaction",
    "Receipt",
    "ReportJob",
]

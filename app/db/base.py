"""SQLAlchemy declarative base for all models."""

from sqlalchemy.orm import declarative_base

# Create declarative base for all models
# Note: Models are NOT imported here to avoid circular imports.
# Models import Base from this module, then models are imported
# separately in migrations/env.py for Alembic auto-detection.
Base = declarative_base()

# Export Base only (models are imported separately as needed)
__all__ = ["Base"]

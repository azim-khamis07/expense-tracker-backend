from sqlalchemy.orm import declarative_base

# Create declarative base for all models
Base = declarative_base()

# Import all models here for Alembic auto-detection
# (We'll add these as we create models)
# from app.models.user import User
# from app.models.category import Category
# from app.models.transaction import Transaction

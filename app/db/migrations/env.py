import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import Base and models (needed for autogenerate)
from app.db.base import Base

# Import all models here for Alembic auto-detection
# This ensures all models are registered with Base.metadata
from app.models.category import Category  # noqa: F401
from app.models.receipt import Receipt  # noqa: F401
from app.models.report_job import ReportJob, ReportStatus  # noqa: F401
from app.models.tag import Tag, transaction_tags  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get DATABASE_URL from environment variable (don't require full Settings)
# This allows migrations to run without all other environment variables
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError(
        "DATABASE_URL environment variable is required for migrations. "
        "Set it in your environment or .env file."
    )

# Remove +asyncpg from URL for SQLAlchemy synchronous engine
sqlalchemy_url = database_url.replace("+asyncpg", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)
config.set_main_option("sqlalchemy.url", sqlalchemy_url)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

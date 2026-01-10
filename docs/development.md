# Development Guide - Phase 1 Complete

## What We Built in Phase 1

### ✅ Database Layer
- Complete database schema with all models
- Proper indexing for performance
- Soft deletes for audit trail
- Foreign key relationships
- Unique constraints
- Migration system with Alembic

### ✅ Security Core
- Password hashing with Argon2
- JWT access + refresh tokens
- Email verification tokens
- Password reset tokens
- Token expiration handling

### ✅ Infrastructure
- Async database session management
- Redis caching with stampede prevention
- Connection pooling
- Health checks

### ✅ Middleware
- Request ID tracking
- Timing middleware
- Structured logging
- Custom exception handling

### ✅ Testing
- Unit tests for security
- Integration test fixtures
- Test database setup
- Coverage reporting

## Common Development Tasks

### Database Operations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1

# View current version
poetry run alembic current

# View history
poetry run alembic history

# View detailed history
poetry run alembic history --verbose
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_security.py

# Run with coverage
poetry run pytest --cov=app

# Run tests matching pattern
poetry run pytest -k "test_password"

# Run with verbose output
poetry run pytest -v

# Run integration tests only
poetry run pytest tests/integration/

# Run unit tests only
poetry run pytest tests/unit/
```

### Code Quality

```bash
# Lint code
poetry run ruff check app/

# Fix auto-fixable issues
poetry run ruff check app/ --fix

# Format code
poetry run black app/ tests/

# Type check
poetry run mypy app/

# Run all quality checks
./scripts/test.sh
```

### Redis Operations

```bash
# Connect to Redis
redis-cli

# Common commands
PING                    # Test connection
KEYS *                  # List all keys
GET key                 # Get value
SET key value           # Set value
DEL key                 # Delete key
FLUSHDB                 # Clear database
TTL key                 # Check expiration
EXPIRE key seconds      # Set expiration
```

### Database Operations

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d expense_tracker

# Common queries
\dt                     # List tables
\d table_name          # Describe table
\di                     # List indexes
\df                     # List functions
\l                      # List databases
\c database_name        # Connect to database
SELECT * FROM users;    # Query data

# View specific table structure
\d users
\d transactions

# Check indexes on a table
\di users*
\di transactions*
```

### Running the Application

```bash
# Start development server
poetry run python -m app.main

# Or use uvicorn directly
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Use helper script
./scripts/dev.sh
```

### Docker Services

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f db redis

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v

# Restart a specific service
docker compose restart db
```

## Project Structure

```
expense-tracker/
├── app/
│   ├── core/           # Configuration, security, exceptions, logging, middleware
│   ├── db/             # Database session, base, migrations
│   ├── infra/          # Redis, S3, queue, cache stampede prevention
│   ├── models/         # SQLAlchemy models (User, Transaction, Category, etc.)
│   ├── modules/        # Feature modules (auth, users, transactions, etc.)
│   ├── utils/          # Utility functions (pagination, datetime)
│   └── main.py         # FastAPI application entry point
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── conftest.py     # Pytest fixtures
├── scripts/            # Helper scripts (dev.sh, test.sh)
├── docs/               # Documentation
├── docker-compose.yml  # Local development services
├── pyproject.toml      # Poetry and tool configurations
└── README.md           # Project overview
```

## Database Models

### User
- Authentication (email, password_hash)
- Email verification
- Password reset tokens
- Account status
- Relationships: categories, tags, transactions, receipts, report_jobs

### Category
- User-specific categories
- Type (expense/income)
- Unique constraint per user
- Relationships: user, transactions

### Tag
- User-specific tags
- Color coding
- Many-to-many with transactions
- Relationships: user, transactions (via transaction_tags)

### Transaction
- Amount, currency, type (expense/income)
- Description, note, occurred_at
- Soft delete (deleted_at)
- Foreign keys: user_id, category_id
- Composite indexes for performance
- Relationships: user, category, tags, receipt

### Receipt
- One-to-one with Transaction
- S3 key, filename, content type, size
- File metadata
- Relationships: transaction, user

### ReportJob
- Async PDF report generation tracking
- Status enum (pending, processing, completed, failed)
- Report parameters (JSON)
- S3 key for generated PDF
- Relationships: user

## API Endpoints

### Health & Info
- `GET /health` - Health check with dependency status
- `GET /api/v1/` - API root endpoint
- `GET /api/v1/docs` - Swagger UI
- `GET /api/v1/redoc` - ReDoc UI
- `GET /api/v1/openapi.json` - OpenAPI schema

## Configuration

### Environment Variables

See `.env.example` for all available configuration options:
- Database connection (PostgreSQL)
- Redis connection
- JWT settings
- AWS S3 (for receipts)
- Celery (for async tasks)
- CORS origins
- Logging level

### Settings Location

All settings are managed via `app/core/config.py` using Pydantic Settings.

## Best Practices

### Code Style
- Use Black for formatting (line length: 100)
- Use Ruff for linting
- Use type hints throughout
- Follow PEP 8 with project-specific adjustments

### Database
- Always use migrations for schema changes
- Never modify existing migrations (create new ones)
- Use async/await for database operations
- Use soft deletes for audit trails
- Add indexes for frequently queried columns

### Testing
- Write unit tests for business logic
- Write integration tests for API endpoints
- Use fixtures for reusable test data
- Aim for 80%+ coverage on critical modules
- Test edge cases and error scenarios

### Git Workflow
- Work on feature branches from `dev`
- Create PRs to `dev` for review
- Merge `dev` → `stage` → `production`
- Keep commits atomic and well-described
- Write meaningful commit messages

## Troubleshooting

### Database Connection Issues
```bash
# Check if database is running
docker compose ps db

# Check database logs
docker compose logs db

# Test connection
psql -h localhost -U postgres -d expense_tracker

# Check if database exists
docker compose exec db psql -U postgres -c "\l" | grep expense_tracker
```

### Migration Issues
```bash
# Check current version
poetry run alembic current

# View migration history
poetry run alembic history

# If stuck, check migration files
ls -la app/db/migrations/versions/

# Rollback if needed
poetry run alembic downgrade -1
```

### Redis Connection Issues
```bash
# Check if Redis is running
docker compose ps redis

# Test Redis connection
redis-cli ping

# View Redis logs
docker compose logs redis

# Check Redis keys
redis-cli KEYS "*"
```

### Test Failures
```bash
# Run tests with verbose output
poetry run pytest -vv

# Run specific failing test
poetry run pytest tests/path/to/test.py::test_name -vv

# Check test database exists
docker compose exec db psql -U postgres -c "\l" | grep expense_tracker_test

# Recreate test database
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS expense_tracker_test;"
docker compose exec db psql -U postgres -c "CREATE DATABASE expense_tracker_test;"
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -ti:8000

# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

## Next Steps

### Phase 2: API Endpoints
- Authentication endpoints (register, login, refresh)
- User management endpoints
- Transaction CRUD endpoints
- Category management endpoints
- Tag management endpoints
- Receipt upload/download endpoints
- Report generation endpoints

### Phase 3: Advanced Features
- Pagination implementation
- Filtering and sorting
- Analytics and reporting
- File upload handling
- Rate limiting
- Email notifications

---

**Last Updated**: Phase 1 Complete  
**Project Status**: ✅ Infrastructure Complete, Ready for API Development

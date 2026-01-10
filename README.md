# 💰 ExpenseTracker - Production-Grade Expense Tracking API

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready expense tracking backend with JWT authentication, CRUD operations, analytics, receipt uploads, and async PDF report generation.

## 🚀 Features

### Core MVP
- ✅ User authentication (JWT with access & refresh tokens)
- ✅ CRUD operations for transactions (expense/income)
- ✅ Categories and tags management
- ✅ Advanced filtering (date range, category, amount)
- ✅ Monthly summaries and analytics
- ✅ Dashboard with chart-ready aggregates
- ✅ Receipt upload to S3 with presigned URLs
- ✅ Async PDF report generation (Celery)

### Technical Highlights
- 🏗️ Clean architecture (Router → Service → Repository)
- 🔒 Production-grade security (Argon2, rate limiting, CORS)
- 📊 Optimized queries with proper indexing
- 💾 Redis caching with stampede prevention
- 🐳 Docker Compose for local development
- ✅ 80%+ test coverage
- 📝 Auto-generated OpenAPI documentation

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15
- Redis 7
- AWS account (for S3)

## 🛠️ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/expense-tracker.git
cd expense-tracker
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Docker services
```bash
docker compose up -d
```

### 4. Install dependencies
```bash
poetry install
```

### 5. Run database migrations
```bash
poetry run alembic upgrade head
```

### 6. Start the development server
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000/api/v1/
- **Docs**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## 📁 Project Structure

```
expense-tracker/
├── app/
│   ├── core/           # Configuration, security, exceptions
│   ├── db/             # Database session and migrations
│   ├── infra/          # Redis, S3, Celery queue
│   ├── models/         # SQLAlchemy models
│   ├── modules/        # Feature modules (auth, users, etc.)
│   ├── utils/          # Utility functions
│   └── main.py         # FastAPI application
├── tests/              # Test suite
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docker/             # Docker-related files
├── docker-compose.yml  # Local development services
├── pyproject.toml      # Poetry and tool configurations
└── README.md           # This file
```

## 🧪 Testing

Run all tests:
```bash
poetry run pytest
```

Run with coverage:
```bash
poetry run pytest --cov=app --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

## 🔧 Development Tools

### Code Quality
- **Ruff**: Linting (`poetry run ruff check .`)
- **Black**: Formatting (`poetry run black .`)
- **MyPy**: Type checking (`poetry run mypy .`)

### Database Migrations
```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## 🐳 Docker Services

The `docker-compose.yml` includes:
- **PostgreSQL**: Database (port 5432)
- **Redis**: Cache and message broker (port 6379)
- **pgAdmin**: Database management (port 5050)
- **Redis Commander**: Redis management (port 8081)

## 📝 Environment Variables

See `.env.example` for all required environment variables.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

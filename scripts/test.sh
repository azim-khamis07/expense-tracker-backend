#!/bin/bash
set -e

echo "🧪 Running test suite..."

# Run linting
echo "📝 Linting code..."
poetry run ruff check app/

# Run type checking
echo "🔍 Type checking..."
poetry run mypy app/

# Run tests with coverage
echo "✅ Running tests..."
poetry run pytest --cov=app --cov-report=term-missing

echo "✨ All checks passed!"

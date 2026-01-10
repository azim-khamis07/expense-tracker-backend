#!/bin/bash
set -e

echo "🚀 Starting ExpenseTracker Development Environment"

# Start Docker services
echo "📦 Starting Docker services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check database connection
echo "🔍 Checking database connection..."
until docker compose exec -T db pg_isready -U postgres; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Run migrations
echo "🔄 Running database migrations..."
poetry run alembic upgrade head

# Start development server
echo "✅ Starting development server..."
poetry run python -m app.main

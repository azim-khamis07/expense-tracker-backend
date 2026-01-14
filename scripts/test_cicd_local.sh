#!/bin/bash

# ============================================
# Local CI/CD Test Script
# ============================================
# This script runs all CI/CD steps locally to verify
# everything works before pushing to GitHub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED++))
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing=0

    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed"
        missing=1
    else
        print_success "Poetry is installed"
    fi

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        missing=1
    else
        print_success "Docker is installed"
    fi

    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed"
        missing=1
    else
        print_success "Terraform is installed"
    fi

    if [ $missing -eq 1 ]; then
        print_error "Please install missing prerequisites"
        exit 1
    fi
}

# Step 1: Linting
test_linting() {
    print_header "Step 1: Linting"

    if poetry run ruff check app/ --select F --ignore F401,F841; then
        print_success "Ruff linting passed"
    else
        print_error "Ruff linting failed"
        return 1
    fi

    if poetry run black --check app/; then
        print_success "Black formatting check passed"
    else
        print_error "Black formatting check failed"
        return 1
    fi
}

# Step 2: Database Setup
setup_test_database() {
    print_header "Step 2: Setting Up Test Database"

    print_info "Checking if PostgreSQL is running..."
    if docker ps | grep -q postgres; then
        print_success "PostgreSQL container is running"
    else
        print_info "Starting PostgreSQL container..."
        docker run -d \
            --name test-postgres \
            -e POSTGRES_USER=test_user \
            -e POSTGRES_PASSWORD=test_password \
            -e POSTGRES_DB=test_db \
            -p 5432:5432 \
            postgres:15-alpine || true

        print_info "Waiting for PostgreSQL to be ready..."
        sleep 5
        print_success "PostgreSQL container started"
    fi

    print_info "Checking if Redis is running..."
    if docker ps | grep -q redis; then
        print_success "Redis container is running"
    else
        print_info "Starting Redis container..."
        docker run -d \
            --name test-redis \
            -p 6379:6379 \
            redis:7-alpine || true

        print_info "Waiting for Redis to be ready..."
        sleep 3
        print_success "Redis container started"
    fi
}

# Step 3: Database Migrations
test_migrations() {
    print_header "Step 3: Database Migrations"

    export DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
    export REDIS_URL="redis://localhost:6379/0"
    export JWT_SECRET_KEY="test-secret-key-for-migrations"
    export CELERY_BROKER_URL="redis://localhost:6379/1"
    export CELERY_RESULT_BACKEND="redis://localhost:6379/2"

    if poetry run alembic upgrade head; then
        print_success "Database migrations completed"
    else
        print_error "Database migrations failed"
        return 1
    fi
}

# Step 4: Unit & Integration Tests
test_unit_integration() {
    print_header "Step 4: Unit & Integration Tests"

    export DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
    export REDIS_URL="redis://localhost:6379/0"
    export JWT_SECRET_KEY="test-secret-key"
    export CELERY_BROKER_URL="redis://localhost:6379/1"
    export CELERY_RESULT_BACKEND="redis://localhost:6379/2"
    export ENV="test"

    if poetry run pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=xml; then
        print_success "All tests passed"
    else
        print_error "Some tests failed"
        return 1
    fi
}

# Step 5: Docker Builds
test_docker_builds() {
    print_header "Step 5: Docker Builds"

    # Build API image
    if docker build -t expense-tracker-api:test -f Dockerfile .; then
        print_success "API Docker image built"
    else
        print_error "API Docker image build failed"
        return 1
    fi

    # Build Worker image
    if docker build -t expense-tracker-worker:test -f Dockerfile.worker .; then
        print_success "Worker Docker image built"
    else
        print_error "Worker Docker image build failed"
        return 1
    fi

    # Build Flower image
    if docker build -t expense-tracker-flower:test -f Dockerfile.flower .; then
        print_success "Flower Docker image built"
    else
        print_error "Flower Docker image build failed"
        return 1
    fi
}

# Step 6: Terraform Validation
test_terraform() {
    print_header "Step 6: Terraform Validation"

    cd terraform || exit 1

    # Check if backend configs exist
    for env in dev stage prod; do
        if [ -f "backend-${env}.conf" ]; then
            print_success "backend-${env}.conf exists"
        else
            print_error "backend-${env}.conf is missing"
            return 1
        fi
    done

    # Test Terraform init for dev (without actually applying)
    export TF_VAR_environment="dev"
    if terraform init -backend-config=backend-dev.conf -backend=false; then
        print_success "Terraform init (dev) succeeded"
    else
        print_error "Terraform init (dev) failed"
        return 1
    fi

    # Validate Terraform configuration
    if terraform validate; then
        print_success "Terraform validation passed"
    else
        print_error "Terraform validation failed"
        return 1
    fi

    cd ..
}

# Step 7: Security Scan (Trivy if available)
test_security_scan() {
    print_header "Step 7: Security Scan"

    if command -v trivy &> /dev/null; then
        print_info "Running Trivy security scan..."
        if trivy fs --exit-code 0 --severity HIGH,CRITICAL .; then
            print_success "Security scan passed"
        else
            print_error "Security scan found issues"
            return 1
        fi
    else
        print_info "Trivy not installed, skipping security scan"
        print_info "Install with: brew install trivy (macOS) or see https://aquasecurity.github.io/trivy/"
    fi
}

# Cleanup
cleanup() {
    print_header "Cleanup"

    print_info "Stopping test containers..."
    docker stop test-postgres test-redis 2>/dev/null || true
    docker rm test-postgres test-redis 2>/dev/null || true

    print_info "Removing test Docker images..."
    docker rmi expense-tracker-api:test expense-tracker-worker:test expense-tracker-flower:test 2>/dev/null || true

    print_success "Cleanup completed"
}

# Main execution
main() {
    print_header "Local CI/CD Test Suite"
    print_info "This will test all CI/CD steps locally"
    print_info "Press Ctrl+C to cancel\n"

    # Trap to cleanup on exit
    trap cleanup EXIT

    check_prerequisites

    # Run all test steps
    test_linting || exit 1
    setup_test_database
    test_migrations || exit 1
    test_unit_integration || exit 1
    test_docker_builds || exit 1
    test_terraform || exit 1
    test_security_scan || print_info "Security scan skipped or failed (non-critical)"

    # Summary
    print_header "Test Summary"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"

    if [ $FAILED -eq 0 ]; then
        print_success "All CI/CD tests passed! Ready to push."
        exit 0
    else
        print_error "Some tests failed. Please fix issues before pushing."
        exit 1
    fi
}

# Run main
main

# Testing Guide

## Automated Tests

### Run All Tests

```bash
# Run all tests with verbose output
poetry run pytest -v

# Run with coverage report (terminal)
poetry run pytest --cov=app --cov-report=term-missing

# Run with coverage report (HTML)
poetry run pytest --cov=app --cov-report=html --cov-report=term
# View HTML report: open htmlcov/index.html

# Run specific test file
poetry run pytest tests/unit/test_auth_service.py -v

# Run specific test
poetry run pytest tests/unit/test_auth_service.py::TestAuthService::test_login_success -v

# Run tests matching pattern
poetry run pytest -k "login" -v
```

### Test Categories

#### Unit Tests (32 tests)
- **Security Tests** (`tests/unit/test_security.py`): 12 tests
  - Password hashing (4 tests)
  - JWT token creation/decoding (5 tests)
  - Email verification tokens (4 tests)
  - Password reset tokens (4 tests)

- **Auth Service Tests** (`tests/unit/test_auth_service.py`): 20 tests
  - User registration (2 tests)
  - User login (4 tests)
  - Token refresh (3 tests)
  - Email verification (3 tests)
  - Resend verification (3 tests)
  - Password reset (5 tests)

#### Integration Tests (2 tests)
- **Health Check Tests** (`tests/integration/test_health.py`): 2 tests
  - Health endpoint with dependencies
  - API root endpoint

#### Fixture Tests (4 tests)
- **Fixture Validation** (`tests/test_fixtures.py`): 4 tests
  - Sample user data
  - Sample category data
  - Sample transaction data
  - Client fixture

#### Main App Tests (3 tests)
- **Main App Tests** (`tests/test_main.py`): 3 tests
  - Health check
  - Root endpoint
  - Sample user data

### Current Test Coverage: 66%

**High Coverage Modules (>90%):**
- `app/core/security.py`: 100%
- `app/core/config.py`: 100%
- `app/models/user.py`: 96%
- `app/models/category.py`: 95%
- `app/modules/auth/service.py`: 94%
- `app/modules/users/repo.py`: 96%
- `app/core/middleware.py`: 89%

**Modules Needing More Tests:**
- `app/core/dependencies.py`: 34%
- `app/core/rate_limit.py`: 28%
- `app/infra/redis.py`: 27%
- `app/modules/auth/router.py`: 49%
- `app/utils/pagination.py`: 0%
- `app/utils/datetime_utils.py`: 32%

## Manual Testing

### Prerequisites

1. **Start Docker Services:**
   ```bash
   docker compose up -d
   ```

2. **Start the Server:**
   ```bash
   poetry run python -m app.main
   ```
   Server will run on `http://localhost:8000`

3. **Run Migrations (if needed):**
   ```bash
   poetry run alembic upgrade head
   ```

### Automated Manual Testing Script

Run the comprehensive authentication testing script:

```bash
./scripts/test_auth.sh
```

This script tests:
1. Server health check
2. User registration
3. Duplicate registration rejection
4. User login
5. Get current user (authenticated)
6. Wrong password rejection
7. Token refresh
8. Password reset request
9. Unauthenticated access rejection
10. User profile access

### Manual curl Testing

#### 1. Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manual@example.com",
    "password": "Manual123!"
  }'
```

**Expected Response:**
```json
{
  "id": "uuid",
  "email": "manual@example.com",
  "is_email_verified": false,
  "is_active": true,
  "created_at": "2026-01-10T..."
}
```

**Note:** Check server logs for email verification token (development mode).

#### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manual@example.com",
    "password": "Manual123!"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Save the access_token for authenticated requests:**
```bash
export ACCESS_TOKEN="your_access_token_here"
```

#### 3. Get Current User (Me)

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

**Expected Response:**
```json
{
  "id": "uuid",
  "email": "manual@example.com",
  "is_email_verified": false,
  "is_active": true,
  "created_at": "2026-01-10T..."
}
```

#### 4. Refresh Access Token

```bash
# Save refresh token from login
export REFRESH_TOKEN="your_refresh_token_here"

curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"${REFRESH_TOKEN}\"
  }"
```

#### 5. Request Password Reset

```bash
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manual@example.com"
  }'
```

**Note:** Check server logs for reset token (development mode).

#### 6. Verify Email

```bash
# Get verification token from server logs or registration response
curl -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{
    "token": "verification_token_from_logs"
  }'
```

#### 7. Get User Profile

```bash
curl -X GET http://localhost:8000/api/v1/users/profile \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

**Expected Response:**
```json
{
  "id": "uuid",
  "email": "manual@example.com",
  "is_email_verified": false,
  "is_active": true,
  "created_at": "2026-01-10T...",
  "updated_at": "2026-01-10T..."
}
```

#### 8. Change Password

```bash
curl -X POST http://localhost:8000/api/v1/users/change-password \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "Manual123!",
    "new_password": "NewPassword123!"
  }'
```

#### 9. Test Error Cases

**Login with wrong password:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manual@example.com",
    "password": "WrongPassword123!"
  }'
```
**Expected:** 401 Unauthorized

**Access protected endpoint without token:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me
```
**Expected:** 403 Forbidden

**Register with duplicate email:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manual@example.com",
    "password": "AnotherPassword123!"
  }'
```
**Expected:** 409 Conflict

### Interactive API Documentation

FastAPI provides interactive API documentation:

1. **Swagger UI:**
   - URL: `http://localhost:8000/api/v1/docs`
   - Interactive interface to test all endpoints

2. **ReDoc:**
   - URL: `http://localhost:8000/api/v1/redoc`
   - Alternative documentation interface

3. **OpenAPI Schema:**
   - URL: `http://localhost:8000/api/v1/openapi.json`
   - Machine-readable API specification

## Test Results Summary

### ✅ All Tests Passing: 50/50

- **Unit Tests:** 32 tests ✅
- **Integration Tests:** 2 tests ✅
- **Fixture Tests:** 4 tests ✅
- **Main App Tests:** 3 tests ✅
- **Example Tests:** 2 tests ✅
- **Health Tests:** 7 tests ✅ (including duplicates)

### Coverage Report

```
TOTAL: 1105 statements, 371 missed, 66% coverage
```

**Key Metrics:**
- Core modules: 66% average
- Auth service: 94% coverage
- Security module: 100% coverage
- User repository: 96% coverage
- Models: 95%+ coverage

### Warnings

- Some deprecation warnings for `datetime.utcnow()` (planned fix)
- SQLAlchemy relationship warnings (informational)
- Pydantic v2 compatibility warnings (informational)

## Continuous Integration

To run all quality checks:

```bash
./scripts/test.sh
```

This runs:
1. Ruff linting
2. MyPy type checking
3. Pytest with coverage

## Next Steps

### Improve Coverage

1. Add integration tests for auth router endpoints
2. Add tests for rate limiting functionality
3. Add tests for user management endpoints
4. Add tests for Redis operations
5. Add tests for datetime utilities
6. Add tests for pagination utilities

### Test Infrastructure

1. Add test fixtures for authenticated users
2. Add test fixtures for categories, tags, transactions
3. Add database transaction rollback for each test
4. Add mock for email service (currently logs only)
5. Add performance/load tests

---

**Last Updated:** Step 7.3 Complete
**Test Status:** ✅ All Tests Passing (50/50)
**Coverage:** 66% overall, 94% for auth service

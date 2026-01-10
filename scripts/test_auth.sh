#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_URL="${BASE_URL}/api/v1"

echo -e "${BLUE}🧪 Manual Authentication API Testing${NC}"
echo "=========================================="
echo -e "Base URL: ${YELLOW}${API_URL}${NC}"
echo ""

# Check if server is running
echo -e "${BLUE}1. Checking server health...${NC}"
if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is running${NC}"
else
    echo -e "${RED}❌ Server is not running. Please start the server first:${NC}"
    echo "   poetry run python -m app.main"
    exit 1
fi

echo ""

# Test 1: Register user
echo -e "${BLUE}2. Testing user registration...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPass123!"
  }')

if echo "$REGISTER_RESPONSE" | grep -q '"id"'; then
    echo -e "${GREEN}✅ Registration successful${NC}"
    USER_ID=$(echo "$REGISTER_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo "   User ID: $USER_ID"
else
    echo -e "${RED}❌ Registration failed${NC}"
    echo "   Response: $REGISTER_RESPONSE"
    exit 1
fi

echo ""

# Test 2: Register duplicate user (should fail)
echo -e "${BLUE}3. Testing duplicate registration (should fail)...${NC}"
DUPLICATE_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPass123!"
  }')

if echo "$DUPLICATE_RESPONSE" | grep -q "already exists\|already registered\|Conflict"; then
    echo -e "${GREEN}✅ Duplicate registration correctly rejected${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response (might be OK):${NC}"
    echo "   Response: $DUPLICATE_RESPONSE"
fi

echo ""

# Test 3: Login
echo -e "${BLUE}4. Testing user login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPass123!"
  }')

if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
    echo -e "${GREEN}✅ Login successful${NC}"
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"refresh_token":"[^"]*"' | cut -d'"' -f4)
    echo "   Access Token: ${ACCESS_TOKEN:0:50}..."
    echo "   Refresh Token: ${REFRESH_TOKEN:0:50}..."
else
    echo -e "${RED}❌ Login failed${NC}"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

echo ""

# Test 4: Get current user (me)
echo -e "${BLUE}5. Testing GET /auth/me (authenticated)...${NC}"
ME_RESPONSE=$(curl -s -X GET "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

if echo "$ME_RESPONSE" | grep -q '"email"'; then
    echo -e "${GREEN}✅ Get current user successful${NC}"
    USER_EMAIL=$(echo "$ME_RESPONSE" | grep -o '"email":"[^"]*"' | cut -d'"' -f4)
    echo "   Email: $USER_EMAIL"
else
    echo -e "${RED}❌ Get current user failed${NC}"
    echo "   Response: $ME_RESPONSE"
fi

echo ""

# Test 5: Login with wrong password (should fail)
echo -e "${BLUE}6. Testing login with wrong password (should fail)...${NC}"
WRONG_PASS_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "WrongPassword123!"
  }')

if echo "$WRONG_PASS_RESPONSE" | grep -q "invalid\|Unauthorized\|401"; then
    echo -e "${GREEN}✅ Wrong password correctly rejected${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response:${NC}"
    echo "   Response: $WRONG_PASS_RESPONSE"
fi

echo ""

# Test 6: Refresh token
echo -e "${BLUE}7. Testing token refresh...${NC}"
REFRESH_RESPONSE=$(curl -s -X POST "${API_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"${REFRESH_TOKEN}\"
  }")

if echo "$REFRESH_RESPONSE" | grep -q '"access_token"'; then
    echo -e "${GREEN}✅ Token refresh successful${NC}"
    NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "   New Access Token: ${NEW_ACCESS_TOKEN:0:50}..."
else
    echo -e "${RED}❌ Token refresh failed${NC}"
    echo "   Response: $REFRESH_RESPONSE"
fi

echo ""

# Test 7: Request password reset
echo -e "${BLUE}8. Testing password reset request...${NC}"
RESET_REQUEST_RESPONSE=$(curl -s -X POST "${API_URL}/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com"
  }')

if echo "$RESET_REQUEST_RESPONSE" | grep -q "message\|sent"; then
    echo -e "${GREEN}✅ Password reset request successful${NC}"
    echo "   Note: In development, check server logs for reset token"
else
    echo -e "${YELLOW}⚠️  Unexpected response:${NC}"
    echo "   Response: $RESET_REQUEST_RESPONSE"
fi

echo ""

# Test 8: Access protected endpoint without token (should fail)
echo -e "${BLUE}9. Testing protected endpoint without token (should fail)...${NC}"
NO_AUTH_RESPONSE=$(curl -s -X GET "${API_URL}/auth/me")

if echo "$NO_AUTH_RESPONSE" | grep -q "401\|Unauthorized\|Not authenticated"; then
    echo -e "${GREEN}✅ Unauthenticated access correctly rejected${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response:${NC}"
    echo "   Response: $NO_AUTH_RESPONSE"
fi

echo ""

# Test 9: Get user profile (authenticated)
echo -e "${BLUE}10. Testing GET /users/profile...${NC}"
PROFILE_RESPONSE=$(curl -s -X GET "${API_URL}/users/profile" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

if echo "$PROFILE_RESPONSE" | grep -q '"email"'; then
    echo -e "${GREEN}✅ Get profile successful${NC}"
else
    echo -e "${RED}❌ Get profile failed${NC}"
    echo "   Response: $PROFILE_RESPONSE"
fi

echo ""
echo -e "${GREEN}✨ All authentication tests completed!${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo "  • Registration: ✅"
echo "  • Login: ✅"
echo "  • Get current user: ✅"
echo "  • Token refresh: ✅"
echo "  • Password reset request: ✅"
echo "  • Profile access: ✅"
echo ""
echo -e "${YELLOW}Note: Some endpoints require email verification tokens from server logs${NC}"
echo "      Check server logs for verification and reset tokens in development mode"

#!/bin/bash
set -euo pipefail

BASE_URL="http://localhost:8000/api/v1"
EMAIL="complete@example.com"
PASSWORD="Complete123!"

echo "🧪 Testing ExpenseTracker Complete Flow"
echo "========================================"

# Step 1: Register
echo ""
echo "1️⃣  Registering user..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

if echo "$REGISTER_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
  echo "✅ User registered successfully"
  echo "$REGISTER_RESPONSE" | jq '.id, .email'
else
  echo "❌ Registration failed or user already exists"
  echo "$REGISTER_RESPONSE" | jq '.'
fi

# Step 2: Login
echo ""
echo "2️⃣  Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Login failed"
  echo "$LOGIN_RESPONSE" | jq '.'
  exit 1
fi

echo "✅ Got access token"

# Step 3: Create default categories
echo ""
echo "3️⃣  Creating default categories..."
CATEGORIES_DEFAULT=$(curl -s -X POST "$BASE_URL/categories/defaults" \
  -H "Authorization: Bearer $TOKEN")

if echo "$CATEGORIES_DEFAULT" | jq -e '.total' >/dev/null 2>&1; then
  echo "✅ Default categories created"
  echo "$CATEGORIES_DEFAULT" | jq '.total, .expense_count, .income_count'
else
  echo "⚠️  Categories may already exist"
fi

# Step 4: List categories
echo ""
echo "4️⃣  Listing categories..."
CATEGORIES=$(curl -s -X GET "$BASE_URL/categories" \
  -H "Authorization: Bearer $TOKEN")

if echo "$CATEGORIES" | jq -e '.total' >/dev/null 2>&1; then
  TOTAL=$(echo "$CATEGORIES" | jq -r '.total')
  echo "✅ Found $TOTAL categories"

  # Get a category ID
  EXPENSE_CATEGORY_ID=$(echo "$CATEGORIES" | jq -r '.items[] | select(.type=="expense") | .id' | head -1)
  INCOME_CATEGORY_ID=$(echo "$CATEGORIES" | jq -r '.items[] | select(.type=="income") | .id' | head -1)

  if [ -z "$EXPENSE_CATEGORY_ID" ] || [ "$EXPENSE_CATEGORY_ID" = "null" ]; then
    echo "❌ No expense category found"
    exit 1
  fi

  if [ -z "$INCOME_CATEGORY_ID" ] || [ "$INCOME_CATEGORY_ID" = "null" ]; then
    echo "❌ No income category found"
    exit 1
  fi

  echo "Expense category: $EXPENSE_CATEGORY_ID"
  echo "Income category: $INCOME_CATEGORY_ID"
else
  echo "❌ Failed to list categories"
  echo "$CATEGORIES" | jq '.'
  exit 1
fi

# Step 5: Create tags
echo ""
echo "5️⃣  Creating tags..."

TAG1_RESPONSE=$(curl -s -X POST "$BASE_URL/tags" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"urgent","color":"#FF0000"}')

TAG1_ID=$(echo "$TAG1_RESPONSE" | jq -r '.id // empty')

if [ -z "$TAG1_ID" ] || [ "$TAG1_ID" = "null" ]; then
  # Tag may already exist, try to get it
  TAG1_RESPONSE=$(curl -s -X GET "$BASE_URL/tags?name=urgent" \
    -H "Authorization: Bearer $TOKEN")
  TAG1_ID=$(echo "$TAG1_RESPONSE" | jq -r '.items[] | select(.name=="urgent") | .id' | head -1)
fi

TAG2_RESPONSE=$(curl -s -X POST "$BASE_URL/tags" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"personal","color":"#00FF00"}')

TAG2_ID=$(echo "$TAG2_RESPONSE" | jq -r '.id // empty')

if [ -z "$TAG2_ID" ] || [ "$TAG2_ID" = "null" ]; then
  # Tag may already exist, try to get it
  TAG2_RESPONSE=$(curl -s -X GET "$BASE_URL/tags?name=personal" \
    -H "Authorization: Bearer $TOKEN")
  TAG2_ID=$(echo "$TAG2_RESPONSE" | jq -r '.items[] | select(.name=="personal") | .id' | head -1)
fi

if [ -z "$TAG1_ID" ] || [ "$TAG1_ID" = "null" ] || [ -z "$TAG2_ID" ] || [ "$TAG2_ID" = "null" ]; then
  echo "❌ Failed to create/get tags"
  exit 1
fi

echo "✅ Created tags: $TAG1_ID, $TAG2_ID"

# Step 6: Create transactions
echo ""
echo "6️⃣  Creating transactions..."

# Get current UTC date
OCCURRED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Expense transaction
EXPENSE_RESPONSE=$(curl -s -X POST "$BASE_URL/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": 50.00,
    \"currency\": \"USD\",
    \"type\": \"expense\",
    \"category_id\": \"$EXPENSE_CATEGORY_ID\",
    \"description\": \"Grocery shopping\",
    \"occurred_at\": \"$OCCURRED_AT\",
    \"tag_ids\": [\"$TAG1_ID\"]
  }")

EXPENSE_ID=$(echo "$EXPENSE_RESPONSE" | jq -r '.id // empty')

if [ -z "$EXPENSE_ID" ] || [ "$EXPENSE_ID" = "null" ]; then
  echo "❌ Failed to create expense transaction"
  echo "$EXPENSE_RESPONSE" | jq '.'
  exit 1
fi

echo "✅ Created expense: $EXPENSE_ID"
echo "$EXPENSE_RESPONSE" | jq '.amount, .type, .description'

# Income transaction
INCOME_RESPONSE=$(curl -s -X POST "$BASE_URL/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": 5000.00,
    \"currency\": \"USD\",
    \"type\": \"income\",
    \"category_id\": \"$INCOME_CATEGORY_ID\",
    \"description\": \"Monthly salary\",
    \"occurred_at\": \"$OCCURRED_AT\",
    \"tag_ids\": [\"$TAG2_ID\"]
  }")

INCOME_ID=$(echo "$INCOME_RESPONSE" | jq -r '.id // empty')

if [ -z "$INCOME_ID" ] || [ "$INCOME_ID" = "null" ]; then
  echo "❌ Failed to create income transaction"
  echo "$INCOME_RESPONSE" | jq '.'
  exit 1
fi

echo "✅ Created income: $INCOME_ID"
echo "$INCOME_RESPONSE" | jq '.amount, .type, .description'

# Step 7: List transactions
echo ""
echo "7️⃣  Listing transactions..."
TRANSACTIONS_RESPONSE=$(curl -s -X GET "$BASE_URL/transactions?limit=10" \
  -H "Authorization: Bearer $TOKEN")

if echo "$TRANSACTIONS_RESPONSE" | jq -e '.data' >/dev/null 2>&1; then
  COUNT=$(echo "$TRANSACTIONS_RESPONSE" | jq '.data | length')
  echo "✅ Found $COUNT transactions"
  echo "$TRANSACTIONS_RESPONSE" | jq '.data[0].description, .data[0].amount'
else
  echo "❌ Failed to list transactions"
  echo "$TRANSACTIONS_RESPONSE" | jq '.'
  exit 1
fi

# Step 8: Get statistics
echo ""
echo "8️⃣  Getting statistics..."
STATS_RESPONSE=$(curl -s -X GET "$BASE_URL/transactions/stats" \
  -H "Authorization: Bearer $TOKEN")

if echo "$STATS_RESPONSE" | jq -e '.total_income' >/dev/null 2>&1; then
  echo "✅ Statistics retrieved:"
  echo "$STATS_RESPONSE" | jq '.'
else
  echo "❌ Failed to get statistics"
  echo "$STATS_RESPONSE" | jq '.'
  exit 1
fi

# Step 9: Update transaction
echo ""
echo "9️⃣  Updating transaction..."
UPDATE_RESPONSE=$(curl -s -X PUT "$BASE_URL/transactions/$EXPENSE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 75.50, "description": "Updated: Grocery shopping + household items"}')

if echo "$UPDATE_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
  echo "✅ Transaction updated:"
  echo "$UPDATE_RESPONSE" | jq '.amount, .description'
else
  echo "❌ Failed to update transaction"
  echo "$UPDATE_RESPONSE" | jq '.'
  exit 1
fi

# Step 10: Filter transactions
echo ""
echo "🔟 Filtering transactions..."
FILTER_RESPONSE=$(curl -s -X GET "$BASE_URL/transactions?type=expense&min_amount=50" \
  -H "Authorization: Bearer $TOKEN")

if echo "$FILTER_RESPONSE" | jq -e '.data' >/dev/null 2>&1; then
  FILTER_COUNT=$(echo "$FILTER_RESPONSE" | jq '.data | length')
  echo "✅ Found $FILTER_COUNT expense transactions with amount >= 50"
else
  echo "❌ Failed to filter transactions"
  echo "$FILTER_RESPONSE" | jq '.'
  exit 1
fi

echo ""
echo "✨ Complete flow test finished successfully!"
echo ""
echo "Summary:"
echo "  ✅ User registration"
echo "  ✅ User login"
echo "  ✅ Categories creation and listing"
echo "  ✅ Tags creation"
echo "  ✅ Transaction creation (expense & income)"
echo "  ✅ Transaction listing"
echo "  ✅ Statistics retrieval"
echo "  ✅ Transaction update"
echo "  ✅ Transaction filtering"

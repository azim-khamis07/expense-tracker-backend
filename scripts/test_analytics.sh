#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"
EMAIL="analytics@example.com"
PASSWORD="Analytics123!"

echo "🧪 Testing ExpenseTracker Analytics"
echo "===================================="

# Step 1: Register and login
echo ""
echo "1️⃣  Setting up user..."
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" > /dev/null

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
echo "✅ Logged in"

# Step 2: Create default categories
echo ""
echo "2️⃣  Creating categories..."
curl -s -X POST "$BASE_URL/categories/defaults" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "✅ Categories created"

# Step 3: Create test transactions
echo ""
echo "3️⃣  Creating test transactions (this may take a moment)..."

# Get category IDs
CATEGORIES=$(curl -s -X GET "$BASE_URL/categories" \
  -H "Authorization: Bearer $TOKEN")
EXPENSE_CAT=$(echo "$CATEGORIES" | jq -r '.items[] | select(.type=="expense") | .id' | head -1)
INCOME_CAT=$(echo "$CATEGORIES" | jq -r '.items[] | select(.type=="income") | .id' | head -1)

# Create 20 transactions spread over 3 months
for i in {1..20}; do
  DAYS_AGO=$((RANDOM % 90))
  AMOUNT=$((50 + RANDOM % 450))
  TYPE=$([ $((i % 3)) -eq 0 ] && echo "income" || echo "expense")
  CAT_ID=$([ "$TYPE" == "income" ] && echo "$INCOME_CAT" || echo "$EXPENSE_CAT")

  DATE=$(date -u -d "${DAYS_AGO} days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${DAYS_AGO}d +%Y-%m-%dT%H:%M:%SZ)

  curl -s -X POST "$BASE_URL/transactions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"amount\": $AMOUNT,
      \"currency\": \"USD\",
      \"type\": \"$TYPE\",
      \"category_id\": \"$CAT_ID\",
      \"description\": \"Test transaction $i\",
      \"occurred_at\": \"$DATE\"
    }" > /dev/null
done

echo "✅ Created 20 test transactions"

# Step 4: Test dashboard
echo ""
echo "4️⃣  Testing dashboard..."
curl -s -X GET "$BASE_URL/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    current_month: .current_month.month,
    total_expense: .current_month.total_expense,
    total_income: .current_month.total_income,
    net: .current_month.net,
    transaction_count: .current_month.transaction_count
  }'

# Step 5: Test category breakdown
echo ""
echo "5️⃣  Testing category breakdown..."
START_DATE=$(date -u -d "30 days ago" +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -v-30d +%Y-%m-%dT00:00:00Z)
END_DATE=$(date -u +%Y-%m-%dT23:59:59Z)

curl -s -X GET "$BASE_URL/analytics/category-breakdown?start_date=$START_DATE&end_date=$END_DATE" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    total_expense: .total_expense,
    total_income: .total_income,
    expense_categories: .expense_breakdown | length,
    income_categories: .income_breakdown | length
  }'

# Step 6: Test trends
echo ""
echo "6️⃣  Testing trends (daily)..."
curl -s -X GET "$BASE_URL/analytics/trends?start_date=$START_DATE&end_date=$END_DATE&interval=day" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    data_points: .data | length,
    total_income: .total_income,
    total_expense: .total_expense,
    avg_daily_expense: .average_daily_expense
  }'

# Step 7: Test cash flow
echo ""
echo "7️⃣  Testing cash flow (monthly)..."
START_DATE_3M=$(date -u -d "90 days ago" +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -v-90d +%Y-%m-%dT00:00:00Z)

curl -s -X GET "$BASE_URL/analytics/cashflow?start_date=$START_DATE_3M&end_date=$END_DATE&interval=month" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    periods: .data | length,
    cumulative_net: .cumulative_net
  }'

# Step 8: Test cache performance
echo ""
echo "8️⃣  Testing cache performance..."
echo "First request (cold cache):"
time curl -s -X GET "$BASE_URL/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo ""
echo "Second request (warm cache):"
time curl -s -X GET "$BASE_URL/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Step 9: Check Redis cache
echo ""
echo "9️⃣  Checking Redis cache..."
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli KEYS "dash:*" 2>/dev/null | wc -l | xargs echo "Cache keys:" || echo "Redis not available or no cache keys"
else
  echo "redis-cli not found, skipping cache check"
fi

echo ""
echo "✨ Analytics tests completed!"

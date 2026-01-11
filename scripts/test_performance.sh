#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
EMAIL="perf@example.com"
PASSWORD="Performance123!"

echo "⚡ Performance Testing"
echo "====================="

# Setup
echo "Setting up test user..."
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" > /dev/null

TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.access_token')

curl -s -X POST "$BASE_URL/categories/defaults" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

EXPENSE_CAT=$(curl -s -X GET "$BASE_URL/categories" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[] | select(.type=="expense") | .id' | head -1)

echo "Creating 100 transactions..."
for i in {1..100}; do
  DAYS_AGO=$((RANDOM % 365))
  AMOUNT=$((10 + RANDOM % 990))
  DATE=$(date -u -d "${DAYS_AGO} days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${DAYS_AGO}d +%Y-%m-%dT%H:%M:%SZ)

  curl -s -X POST "$BASE_URL/transactions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"amount\": $AMOUNT,
      \"currency\": \"USD\",
      \"type\": \"expense\",
      \"category_id\": \"$EXPENSE_CAT\",
      \"occurred_at\": \"$DATE\"
    }" > /dev/null

  if [ $((i % 20)) -eq 0 ]; then
    echo "  Created $i transactions..."
  fi
done

echo ""
echo "✅ Setup complete. Running performance tests..."
echo ""

# Test 1: Dashboard load time
echo "📊 Dashboard Performance:"
echo "Cold cache (1st request):"
time curl -s -X GET "$BASE_URL/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo ""
echo "Warm cache (2nd request):"
time curl -s -X GET "$BASE_URL/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo ""
echo "Warm cache (3rd request):"
time curl -s -X GET "$BASE_URL/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Test 2: Category breakdown
echo ""
echo "📈 Category Breakdown Performance:"
START=$(date -u -d "365 days ago" +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -v-365d +%Y-%m-%dT00:00:00Z)
END=$(date -u +%Y-%m-%dT23:59:59Z)

echo "Cold cache:"
time curl -s -X GET "$BASE_URL/analytics/category-breakdown?start_date=$START&end_date=$END" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo ""
echo "Warm cache:"
time curl -s -X GET "$BASE_URL/analytics/category-breakdown?start_date=$START&end_date=$END" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Test 3: Trends
echo ""
echo "📉 Trends Performance (365 days, daily):"
echo "Cold cache:"
time curl -s -X GET "$BASE_URL/analytics/trends?start_date=$START&end_date=$END&interval=day" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo ""
echo "Warm cache:"
time curl -s -X GET "$BASE_URL/analytics/trends?start_date=$START&end_date=$END&interval=day" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo ""
echo "✨ Performance tests completed!"
echo ""
echo "Expected performance:"
echo "- Cold cache: < 1s"
echo "- Warm cache: < 200ms"

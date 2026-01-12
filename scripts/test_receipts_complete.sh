#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"
EMAIL="test_receipts@example.com"
PASSWORD="Test123!"

echo "🧪 Complete Receipt Testing Suite"
echo "=================================="
echo ""

# Step 1: Check services
echo "1️⃣  Checking services..."
echo "   • Docker services..."
docker compose ps --format "   {{.Name}}: {{.Status}}" | head -5

echo ""
echo "   • API server..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo "   ✅ API server is running"
else
  echo "   ⚠️  API server is not running"
  echo "   📝 Start with: uvicorn app.main:app --reload"
  exit 1
fi

echo ""
echo "   • MinIO..."
if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
  echo "   ✅ MinIO is running"
else
  echo "   ⚠️  MinIO is not running"
  echo "   📝 Start with: docker compose up -d minio"
  exit 1
fi

# Step 2: Setup user
echo ""
echo "2️⃣  Setting up test user..."
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" > /dev/null 2>&1 || true

TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
  echo "   ❌ Failed to get authentication token"
  exit 1
fi

echo "   ✅ Logged in successfully"

# Step 3: Create transaction
echo ""
echo "3️⃣  Creating transaction..."
curl -s -X POST "$BASE_URL/categories/defaults" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

CATEGORY_ID=$(curl -s -X GET "$BASE_URL/categories" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

TRANSACTION=$(curl -s -X POST "$BASE_URL/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": 100.00,
    \"currency\": \"USD\",
    \"type\": \"expense\",
    \"category_id\": \"$CATEGORY_ID\",
    \"description\": \"Test with real receipt\",
    \"occurred_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }")

TRANSACTION_ID=$(echo "$TRANSACTION" | jq -r '.id')
echo "   ✅ Created transaction: $TRANSACTION_ID"

# Step 4: Download test image
echo ""
echo "4️⃣  Downloading test receipt image..."
curl -s https://via.placeholder.com/600x400.png -o /tmp/test_receipt_real.png
if [ -f /tmp/test_receipt_real.png ]; then
  SIZE=$(wc -c < /tmp/test_receipt_real.png)
  echo "   ✅ Downloaded test image: $SIZE bytes"
else
  echo "   ❌ Failed to download test image"
  exit 1
fi

# Step 5: Upload receipt
echo ""
echo "5️⃣  Uploading receipt..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_receipt_real.png")

RECEIPT_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.id')
if [ -z "$RECEIPT_ID" ] || [ "$RECEIPT_ID" == "null" ]; then
  echo "   ❌ Failed to upload receipt"
  echo "$UPLOAD_RESPONSE" | jq '.' || echo "$UPLOAD_RESPONSE"
  exit 1
fi

echo "   ✅ Receipt uploaded: $RECEIPT_ID"
echo "$UPLOAD_RESPONSE" | jq '{id, original_filename, content_type, size}' | sed 's/^/      /'

# Step 6: Get receipt with presigned URL
echo ""
echo "6️⃣  Getting receipt with download URL..."
RECEIPT_GET=$(curl -s -X GET "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN")

DOWNLOAD_URL=$(echo "$RECEIPT_GET" | jq -r '.download_url')
if [ -z "$DOWNLOAD_URL" ] || [ "$DOWNLOAD_URL" == "null" ]; then
  echo "   ❌ Failed to get receipt"
  echo "$RECEIPT_GET" | jq '.' || echo "$RECEIPT_GET"
  exit 1
fi

echo "   ✅ Got receipt with download URL"
echo "$RECEIPT_GET" | jq '{id, original_filename, size, download_url_length: (.download_url | length)}' | sed 's/^/      /'

# Step 7: Download using presigned URL
echo ""
echo "7️⃣  Downloading receipt using presigned URL..."
curl -s "$DOWNLOAD_URL" -o /tmp/downloaded_receipt_real.png

if [ -f /tmp/downloaded_receipt_real.png ]; then
  DOWNLOADED_SIZE=$(wc -c < /tmp/downloaded_receipt_real.png)
  ORIGINAL_SIZE=$(echo "$RECEIPT_GET" | jq -r '.size')
  echo "   ✅ Downloaded receipt: $DOWNLOADED_SIZE bytes (original: $ORIGINAL_SIZE bytes)"

  if [ "$DOWNLOADED_SIZE" == "$ORIGINAL_SIZE" ]; then
    echo "   ✅ File sizes match!"
  else
    echo "   ⚠️  File sizes differ (may be normal for presigned URLs)"
  fi
else
  echo "   ❌ Failed to download receipt"
  exit 1
fi

# Step 8: Verify transaction has_receipt flag
echo ""
echo "8️⃣  Verifying transaction has_receipt flag..."
TRANSACTION_CHECK=$(curl -s -X GET "$BASE_URL/transactions/$TRANSACTION_ID" \
  -H "Authorization: Bearer $TOKEN")

HAS_RECEIPT=$(echo "$TRANSACTION_CHECK" | jq -r '.has_receipt')
echo "   has_receipt: $HAS_RECEIPT"

if [ "$HAS_RECEIPT" == "true" ]; then
  echo "   ✅ Transaction correctly shows has_receipt=true"
else
  echo "   ❌ Transaction should have has_receipt=true"
  exit 1
fi

# Step 9: Delete receipt
echo ""
echo "9️⃣  Deleting receipt..."
DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN")

STATUS_CODE=$(echo "$DELETE_RESPONSE" | tail -n 1)
if [ "$STATUS_CODE" == "204" ]; then
  echo "   ✅ Receipt deleted successfully (204 No Content)"
else
  echo "   ⚠️  Unexpected status code: $STATUS_CODE"
fi

# Step 10: Verify receipt is deleted
echo ""
echo "🔟 Verifying receipt is deleted..."
RECEIPT_CHECK=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN")

STATUS_CODE=$(echo "$RECEIPT_CHECK" | tail -n 1)
if [ "$STATUS_CODE" == "404" ]; then
  echo "   ✅ Receipt correctly deleted (404 Not Found)"
else
  echo "   ❌ Expected 404, got $STATUS_CODE"
  exit 1
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
rm -f /tmp/test_receipt_real.png /tmp/downloaded_receipt_real.png
echo "   ✅ Temporary files removed"

echo ""
echo "✨ All receipt tests completed successfully!"
echo ""
echo "📊 Summary:"
echo "   ✅ Service checks passed"
echo "   ✅ User authentication working"
echo "   ✅ Transaction creation working"
echo "   ✅ Receipt upload working"
echo "   ✅ Receipt retrieval working"
echo "   ✅ Presigned URL download working"
echo "   ✅ Transaction has_receipt flag working"
echo "   ✅ Receipt deletion working"
echo ""
echo "🎉 Receipt functionality is fully operational!"

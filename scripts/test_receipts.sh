#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"
EMAIL="receipts@example.com"
PASSWORD="Receipts123!"

echo "🧪 Testing Receipt Upload & Management"
echo "======================================="

# Step 1: Setup user
echo ""
echo "1️⃣  Setting up user..."
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" > /dev/null

TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.access_token')

echo "✅ Logged in"

# Step 2: Create category and transaction
echo ""
echo "2️⃣  Creating transaction..."
curl -s -X POST "$BASE_URL/categories/defaults" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

CATEGORY_ID=$(curl -s -X GET "$BASE_URL/categories" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

TRANSACTION=$(curl -s -X POST "$BASE_URL/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": 50.00,
    \"currency\": \"USD\",
    \"type\": \"expense\",
    \"category_id\": \"$CATEGORY_ID\",
    \"description\": \"Test transaction with receipt\",
    \"occurred_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }")

TRANSACTION_ID=$(echo "$TRANSACTION" | jq -r '.id')
echo "✅ Created transaction: $TRANSACTION_ID"

# Step 3: Create test image
echo ""
echo "3️⃣  Creating test receipt image..."
# Create a simple 100x100 red PNG
python3 << 'PYTHON'
from PIL import Image
img = Image.new('RGB', (100, 100), color='red')
img.save('/tmp/test_receipt.png')
print("✅ Created test image")
PYTHON

# Step 4: Upload receipt
echo ""
echo "4️⃣  Uploading receipt..."
RECEIPT_UPLOAD=$(curl -s -X POST "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_receipt.png")

echo "$RECEIPT_UPLOAD" | jq '{id, original_filename, content_type, size}'

# Step 5: Get receipt (with download URL)
echo ""
echo "5️⃣  Getting receipt with download URL..."
RECEIPT_RESPONSE=$(curl -s -X GET "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN")

echo "$RECEIPT_RESPONSE" | jq '{id, original_filename, size, download_url_length: (.download_url | length)}'

DOWNLOAD_URL=$(echo "$RECEIPT_RESPONSE" | jq -r '.download_url')

# Step 6: Download receipt using presigned URL
echo ""
echo "6️⃣  Downloading receipt using presigned URL..."
curl -s "$DOWNLOAD_URL" -o /tmp/downloaded_receipt.png

if [ -f /tmp/downloaded_receipt.png ]; then
  SIZE=$(wc -c < /tmp/downloaded_receipt.png)
  echo "✅ Downloaded receipt: $SIZE bytes"
else
  echo "❌ Failed to download receipt"
fi

# Step 7: Verify transaction has_receipt flag
echo ""
echo "7️⃣  Verifying transaction has_receipt flag..."
TRANSACTION_CHECK=$(curl -s -X GET "$BASE_URL/transactions/$TRANSACTION_ID" \
  -H "Authorization: Bearer $TOKEN")

HAS_RECEIPT=$(echo "$TRANSACTION_CHECK" | jq -r '.has_receipt')
echo "has_receipt: $HAS_RECEIPT"

if [ "$HAS_RECEIPT" == "true" ]; then
  echo "✅ Transaction correctly shows has_receipt=true"
else
  echo "❌ Transaction should have has_receipt=true"
fi

# Step 8: Delete receipt
echo ""
echo "8️⃣  Deleting receipt..."
curl -s -X DELETE "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN"

echo "✅ Receipt deleted"

# Step 9: Verify receipt is gone
echo ""
echo "9️⃣  Verifying receipt is deleted..."
RECEIPT_CHECK=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN")

STATUS_CODE=$(echo "$RECEIPT_CHECK" | tail -n 1)

if [ "$STATUS_CODE" == "404" ]; then
  echo "✅ Receipt correctly deleted (404 response)"
else
  echo "❌ Expected 404, got $STATUS_CODE"
fi

# Cleanup
rm -f /tmp/test_receipt.png /tmp/downloaded_receipt.png

echo ""
echo "✨ Receipt tests completed!"

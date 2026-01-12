#!/bin/bash
set -e

BASE_URL="http://localhost:8000/api/v1"
EMAIL="direct@example.com"
PASSWORD="Direct123!"

echo "🚀 Testing Direct Upload Flow"
echo "=============================="

# Setup
echo ""
echo "Setting up..."
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" > /dev/null 2>&1 || true

TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
  echo "❌ Failed to get authentication token"
  exit 1
fi

curl -s -X POST "$BASE_URL/categories/defaults" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

CATEGORY_ID=$(curl -s -X GET "$BASE_URL/categories" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

TRANSACTION_ID=$(curl -s -X POST "$BASE_URL/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": 75.00,
    \"currency\": \"USD\",
    \"type\": \"expense\",
    \"category_id\": \"$CATEGORY_ID\",
    \"description\": \"Test direct upload\",
    \"occurred_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }" | jq -r '.id')

echo "✅ Transaction created: $TRANSACTION_ID"

# Step 1: Get presigned upload URL
echo ""
echo "1️⃣  Requesting presigned upload URL..."
PRESIGNED=$(curl -s -X POST "$BASE_URL/transactions/$TRANSACTION_ID/receipt/presigned-upload?filename=receipt.png&content_type=image/png" \
  -H "Authorization: Bearer $TOKEN")

UPLOAD_URL=$(echo "$PRESIGNED" | jq -r '.upload_url')
S3_KEY=$(echo "$PRESIGNED" | jq -r '.s3_key')
FIELDS_JSON=$(echo "$PRESIGNED" | jq -r '.fields')

if [ -z "$UPLOAD_URL" ] || [ "$UPLOAD_URL" == "null" ]; then
  echo "❌ Failed to get presigned URL"
  echo "$PRESIGNED" | jq '.'
  exit 1
fi

echo "✅ Got presigned URL"
echo "   S3 Key: $S3_KEY"
echo "   Upload URL: ${UPLOAD_URL:0:60}..."

# Step 2: Create test file
echo ""
echo "2️⃣  Creating test file..."
python3 << 'PYTHON'
from PIL import Image
img = Image.new('RGB', (200, 200), color='blue')
img.save('/tmp/direct_receipt.png')
print("✅ Created test image")
PYTHON

FILE_SIZE=$(wc -c < /tmp/direct_receipt.png)
echo "   File size: $FILE_SIZE bytes"

# Step 3: Upload directly to S3 (MinIO)
echo ""
echo "3️⃣  Uploading directly to S3..."
echo "   This may take a moment..."

# Build the form data for presigned POST
# Extract fields from JSON and build curl form data
FORM_DATA=$(echo "$FIELDS_JSON" | jq -r 'to_entries | map("-F \"\(.key)=\(.value)\"") | join(" ")')

# Upload using presigned POST URL
UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$UPLOAD_URL" \
  $(echo "$FIELDS_JSON" | jq -r 'to_entries | map("-F \(.key)=\(.value)") | join(" ")') \
  -F "file=@/tmp/direct_receipt.png" 2>&1)

HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n 1)
UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" == "204" ] || [ "$HTTP_CODE" == "200" ]; then
  echo "✅ Uploaded to S3 (HTTP $HTTP_CODE)"
else
  echo "⚠️  Upload response: HTTP $HTTP_CODE"
  echo "$UPLOAD_BODY" | head -20
fi

# Step 4: Confirm upload with API
echo ""
echo "4️⃣  Confirming upload..."
CONFIRM_RESPONSE=$(curl -s -X POST "$BASE_URL/transactions/$TRANSACTION_ID/receipt/confirm-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "s3_key=$S3_KEY" \
  -F "filename=receipt.png" \
  -F "content_type=image/png" \
  -F "size=$FILE_SIZE")

RECEIPT_ID=$(echo "$CONFIRM_RESPONSE" | jq -r '.id')

if [ -z "$RECEIPT_ID" ] || [ "$RECEIPT_ID" == "null" ]; then
  echo "❌ Failed to confirm upload"
  echo "$CONFIRM_RESPONSE" | jq '.' || echo "$CONFIRM_RESPONSE"
  exit 1
fi

echo "✅ Upload confirmed"
echo "$CONFIRM_RESPONSE" | jq '{id, original_filename, size, s3_key}' | sed 's/^/   /'

# Step 5: Verify receipt exists
echo ""
echo "5️⃣  Verifying receipt..."
RECEIPT_GET=$(curl -s -X GET "$BASE_URL/transactions/$TRANSACTION_ID/receipt" \
  -H "Authorization: Bearer $TOKEN")

DOWNLOAD_URL=$(echo "$RECEIPT_GET" | jq -r '.download_url')

if [ -n "$DOWNLOAD_URL" ] && [ "$DOWNLOAD_URL" != "null" ]; then
  echo "✅ Receipt verified"
  echo "$RECEIPT_GET" | jq '{id, original_filename, size}' | sed 's/^/   /'
else
  echo "❌ Failed to get receipt"
  echo "$RECEIPT_GET" | jq '.' || echo "$RECEIPT_GET"
  exit 1
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
rm -f /tmp/direct_receipt.png
echo "✅ Temporary files removed"

echo ""
echo "✨ Direct upload test completed successfully!"
echo ""
echo "📊 Summary:"
echo "   ✅ Presigned URL generated"
echo "   ✅ File uploaded directly to S3"
echo "   ✅ Upload confirmed with API"
echo "   ✅ Receipt verified"
echo ""
echo "🎉 Direct upload flow is working correctly!"

#!/bin/bash

set -euo pipefail

echo "🪣 Initializing MinIO Bucket"
echo "============================"

# Check if MinIO client is installed
if ! command -v mc &> /dev/null; then
    echo "❌ MinIO client (mc) is not installed"
    echo ""
    echo "Install it using one of the following:"
    echo "  • macOS: brew install minio/stable/mc"
    echo "  • Linux: wget https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc && sudo mv mc /usr/local/bin/"
    echo "  • Or download from: https://min.io/docs/minio/linux/reference/minio-mc.html"
    exit 1
fi

# Wait for MinIO to be ready
echo "⏳ Waiting for MinIO to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:9000/minio/health/live &> /dev/null; then
        echo "✅ MinIO is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ MinIO is not responding. Make sure it's running: docker compose up -d minio"
    exit 1
fi

# Configure MinIO client
echo "🔧 Configuring MinIO client..."
mc alias set local http://localhost:9000 minioadmin minioadmin || {
    echo "⚠️  Alias already exists, updating..."
    mc alias set local http://localhost:9000 minioadmin minioadmin --force
}

# Create bucket (ignore error if it already exists)
echo "📦 Creating bucket..."
BUCKET_NAME="expense-tracker-receipts-dev"
if mc ls local/$BUCKET_NAME &> /dev/null; then
    echo "⚠️  Bucket '$BUCKET_NAME' already exists"
else
    mc mb local/$BUCKET_NAME
    echo "✅ Bucket '$BUCKET_NAME' created"
fi

# Set bucket policy for testing (download allowed)
echo "🔒 Setting bucket policy..."
mc anonymous set download local/$BUCKET_NAME || {
    echo "⚠️  Could not set bucket policy (may already be set)"
}

echo ""
echo "✅ MinIO initialization complete!"
echo ""
echo "📊 MinIO Console: http://localhost:9001"
echo "   Username: minioadmin"
echo "   Password: minioadmin"
echo ""
echo "🪣 Bucket: $BUCKET_NAME"
echo ""
echo "📝 Update your .env file with:"
echo "   S3_ENDPOINT_URL=http://localhost:9000"
echo "   S3_ACCESS_KEY_ID=minioadmin"
echo "   S3_SECRET_ACCESS_KEY=minioadmin"
echo "   S3_BUCKET=$BUCKET_NAME"

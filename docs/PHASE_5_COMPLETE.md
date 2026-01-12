# Phase 5: Receipts & S3 Integration - Complete ✅

## Overview

Phase 5 implements production-ready receipt management with S3 storage, file validation, and both standard and direct upload flows.

## Features Implemented

### 1. S3 Integration
- **Boto3 Client**: Full S3 client wrapper with retry logic and connection pooling
- **MinIO Support**: Local S3-compatible storage for development
- **Server-Side Encryption**: AES256 encryption for AWS S3 (conditional for MinIO)
- **Configuration**: Flexible configuration for AWS S3 and MinIO

### 2. File Validation
- **Magic Number Verification**: Using `python-magic` for actual file type detection
- **Image Validation**: PIL-based image integrity and dimension checks
- **MIME Type Whitelist**: Strict enforcement of allowed file types
- **File Size Limits**: 10MB maximum file size
- **Dimension Checks**: Image dimensions must be between 10x10 and 10000x10000

### 3. Receipt Upload
- **Multipart Form Upload**: Standard upload via API proxy
- **S3 Storage**: Automatic storage with metadata
- **Database Records**: Receipt metadata stored in PostgreSQL
- **Transaction Linking**: `has_receipt` flag on transactions

### 4. Presigned URLs
- **Download URLs**: Secure, time-limited URLs for file access (1 hour expiry)
- **Upload URLs**: Presigned POST URLs for direct client-to-S3 uploads
- **Security**: No public bucket exposure required
- **Time-Limited**: URLs expire after 1 hour

### 5. Direct Upload Flow
- **Presigned URL Generation**: API endpoint for requesting upload URLs
- **Direct S3 Upload**: Client uploads directly to S3 (no proxy)
- **Confirmation Endpoint**: API endpoint to confirm upload and create database record
- **Benefits**: Better for large files and mobile applications

### 6. Receipt Management
- **Get Receipt**: Retrieve receipt with presigned download URL
- **Delete Receipt**: Removes file from S3 and database record
- **User Ownership**: Verification of transaction ownership
- **Filename Sanitization**: Prevents path traversal attacks

### 7. Security
- **Private Bucket**: No public access required
- **User-Specific Paths**: Files stored in `receipts/{user_id}/{transaction_id}/` structure
- **Path Traversal Prevention**: Filename sanitization
- **Ownership Checks**: Transaction ownership verification on all operations

## Files Added/Modified

### New Files
- `app/modules/receipts/schemas.py` - Receipt Pydantic schemas
- `app/modules/receipts/repo.py` - Receipt repository
- `app/modules/receipts/service.py` - Receipt service layer
- `app/modules/receipts/router.py` - Receipt API endpoints
- `app/utils/file_validation.py` - File validation utilities
- `app/infra/s3.py` - S3 client wrapper
- `app/models/receipt.py` - Receipt SQLAlchemy model
- `scripts/test_receipts.sh` - Receipt integration tests
- `scripts/test_receipts_complete.sh` - Comprehensive receipt tests
- `scripts/test_direct_upload.sh` - Direct upload flow tests
- `scripts/init_minio.sh` - MinIO bucket initialization

### Modified Files
- `app/core/config.py` - Added S3 and file upload settings
- `app/main.py` - Registered receipts router, updated version to 0.5.0
- `app/modules/transactions/service.py` - Added `has_receipt` flag
- `docker-compose.yml` - Added MinIO service
- `.env` / `.env.example` - Added S3 configuration

## Local Development Setup

### 1. Start Services
```bash
docker compose up -d
```

### 2. Initialize MinIO Bucket
```bash
./scripts/init_minio.sh
```

### 3. Set Environment Variables
```bash
export S3_ENDPOINT_URL=http://localhost:9000
export S3_ACCESS_KEY_ID=minioadmin
export S3_SECRET_ACCESS_KEY=minioadmin
export S3_BUCKET=expense-tracker-receipts-dev
```

Or add to `.env` file:
```ini
S3_BUCKET=expense-tracker-receipts-dev
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT_URL=http://localhost:9000

MAX_UPLOAD_SIZE=10485760
ALLOWED_MIME_TYPES=image/jpeg,image/png,image/gif,image/webp,application/pdf
```

### 4. Start API Server
```bash
poetry run uvicorn app.main:app --reload
```

### 5. Access Services
- **API**: http://localhost:8000/api/v1/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Database**: localhost:5432
- **Redis**: localhost:6379

## Production Deployment

### AWS S3 Setup

#### 1. Create S3 Bucket
```bash
aws s3 mb s3://expense-tracker-receipts-prod
```

#### 2. Enable Encryption
```bash
aws s3api put-bucket-encryption \
  --bucket expense-tracker-receipts-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

#### 3. Block Public Access
```bash
aws s3api put-public-access-block \
  --bucket expense-tracker-receipts-prod \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

#### 4. Enable Versioning (Optional)
```bash
aws s3api put-bucket-versioning \
  --bucket expense-tracker-receipts-prod \
  --versioning-configuration Status=Enabled
```

#### 5. Set Lifecycle Policy (Optional)
Create `lifecycle.json`:
```json
{
  "Rules": [{
    "Id": "DeleteOldReceipts",
    "Status": "Enabled",
    "Expiration": {
      "Days": 2555
    }
  }]
}
```

Apply:
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket expense-tracker-receipts-prod \
  --lifecycle-configuration file://lifecycle.json
```

#### 6. Update Environment Variables
```ini
S3_BUCKET=expense-tracker-receipts-prod
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=<IAM_ACCESS_KEY>
S3_SECRET_ACCESS_KEY=<IAM_SECRET_KEY>
S3_ENDPOINT_URL=  # Empty for AWS S3
```

### IAM Policy
Create IAM user with the following policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:HeadObject"
    ],
    "Resource": "arn:aws:s3:::expense-tracker-receipts-prod/*"
  }, {
    "Effect": "Allow",
    "Action": [
      "s3:ListBucket"
    ],
    "Resource": "arn:aws:s3:::expense-tracker-receipts-prod"
  }]
}
```

## Testing

### Run All Tests
```bash
# Unit tests
poetry run pytest -v

# Code coverage
poetry run pytest --cov=app --cov-report=html --cov-report=term

# Receipt integration tests
./scripts/test_receipts.sh

# Direct upload flow tests
./scripts/test_direct_upload.sh

# Comprehensive tests
./scripts/test_receipts_complete.sh
```

### Test Results
- **Unit Tests**: 57 passed
- **Code Coverage**: 64%
- **Integration Tests**: All passing
- **Direct Upload Flow**: Working correctly

## API Endpoints

### Receipt Upload (Standard)
```
POST /api/v1/transactions/{transaction_id}/receipt
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body:
- file: <file>
```

### Get Receipt
```
GET /api/v1/transactions/{transaction_id}/receipt
Authorization: Bearer <token>
```

### Delete Receipt
```
DELETE /api/v1/transactions/{transaction_id}/receipt
Authorization: Bearer <token>
```

### Get Presigned Upload URL
```
POST /api/v1/transactions/{transaction_id}/receipt/presigned-upload?filename=<filename>&content_type=<mime_type>
Authorization: Bearer <token>
```

### Confirm Direct Upload
```
POST /api/v1/transactions/{transaction_id}/receipt/confirm-upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body:
- s3_key: <s3_key>
- filename: <filename>
- content_type: <mime_type>
- size: <size>
```

## Configuration

### Environment Variables
- `S3_BUCKET`: S3 bucket name
- `S3_REGION`: AWS region (default: us-east-1)
- `S3_ACCESS_KEY_ID`: AWS access key ID
- `S3_SECRET_ACCESS_KEY`: AWS secret access key
- `S3_ENDPOINT_URL`: S3 endpoint URL (empty for AWS, http://localhost:9000 for MinIO)
- `MAX_UPLOAD_SIZE`: Maximum file size in bytes (default: 10485760 = 10MB)
- `ALLOWED_MIME_TYPES`: Comma-separated list of allowed MIME types

## Next Steps

Phase 5 is complete! Ready for Phase 6: Async Jobs & PDF Reports.

## Notes

- MinIO doesn't support AWS's `ServerSideEncryption` parameter, so it's conditionally applied only for AWS S3
- File validation uses magic numbers for actual file type detection (not just extensions)
- Presigned URLs expire after 1 hour
- Files are stored with user-specific paths for security
- All receipt operations verify transaction ownership

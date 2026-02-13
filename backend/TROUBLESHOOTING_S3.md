# Troubleshooting: S3 Upload Not Working

## Root Cause

The backend server was started **before** the S3 upload code was added. The server needs to be restarted to load the new code.

## Solution

### 1. Restart the Backend Server

```bash
cd /home/kanke/projects/bluetide/backend
uv run uvicorn src.api.main:app --reload --port 8000
```

The `--reload` flag will auto-reload when code changes, but it doesn't pick up changes made before it was started.

### 2. Test S3 Upload

After restarting, upload a PDF through your frontend. The backend will:
1. Save the PDF locally
2. Calculate file size
3. **Upload to S3** ← This is the new step
4. Process with Azure Content Understanding
5. Save to database with S3 URL and file size

### 3. Verify S3 Upload

Check if files are in S3:
```bash
cd /home/kanke/projects/bluetide/backend
uv run python list_s3_files.py
```

You should see output like:
```
✅ Found 1 files:
  - documents/abc123_filename.pdf (2.45 MB) - 2026-02-02 13:10:00+00:00
```

### 4. Check Backend Logs

Watch for these log messages:
```
INFO:src.storage.s3_service:S3 service initialized for bucket: bluetide-docs
INFO:__main__:PDF uploaded to S3: https://bluetide-docs.s3.eu-north-1.amazonaws.com/documents/...
```

If you see:
```
WARNING:__main__:S3 service not available, skipping S3 upload
```

Then the S3 service failed to initialize. Check your `.env` file has the correct AWS credentials.

## Quick Verification Checklist

- [ ] Backend server restarted with new code
- [ ] Upload a test PDF through frontend
- [ ] Check S3 bucket has the file (`list_s3_files.py`)
- [ ] Check database has `s3_url` and `file_size_bytes`
- [ ] Frontend shows file size in data table

## Common Issues

### Issue: "S3 service not available"
**Solution:** Check `.env` file has all AWS credentials:
```env
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_BUCKET_NAME=bluetide-docs
AWS_REGION=eu-north-1
```

### Issue: "AccessDenied" when uploading
**Solution:** The IAM user needs `s3:PutObject` and `s3:PutObjectAcl` permissions.

### Issue: Files upload but can't be accessed publicly
**Solution:** Each file is uploaded with `ACL: 'public-read'`. If this doesn't work, you may need to:
1. Disable "Block all public access" on the bucket

---

## Datalake S3 Integration

### Required Environment Variables

```env
AWS_ACCESS_KEY_ID=your-aws-access-key-id      # optional with IAM role
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key  # optional with IAM role
AWS_REGION=ap-south-1                         # MUST match the bucket region
AWS_S3_BUCKET_NAME=teclusion-datalake-idp
S3_DATALAKE_PREFIX=datalake/                  # optional (default: datalake/)
S3_SYNC_MAX_FILES=500                         # optional safety limit
API_KEY=                                       # optional; set to protect endpoints
```

> **Important:** `AWS_REGION` **must** be `ap-south-1` for the
> `teclusion-datalake-idp` bucket.  A region mismatch will cause a
> `301 Moved Permanently` error from S3 and the backend will refuse to start.

### Endpoints

| Method | Path                          | Description                       |
|--------|-------------------------------|-----------------------------------|
| GET    | `/api/v1/datalake/s3/list`    | List PDFs under a datalake prefix |
| POST   | `/api/v1/datalake/s3/sync`    | Incrementally ingest PDFs         |

### Listing PDFs

```bash
curl "http://localhost:8000/api/v1/datalake/s3/list?limit=10"
```

### Syncing / Ingesting

```bash
# Ingest up to 5 new/changed PDFs
curl -X POST "http://localhost:8000/api/v1/datalake/s3/sync?limit=5"

# Force re-process everything
curl -X POST "http://localhost:8000/api/v1/datalake/s3/sync?limit=5&force=true"
```

### Idempotency

The sync endpoint stores a `source` identifier on each `Document` row:
`s3:<bucket>:<key>`.  The S3 ETag is stored inside the `metrics` JSON as
`_s3_etag`.  On subsequent syncs:

- **Same key + same ETag** → skipped (already ingested).
- **Same key + different ETag** → old chunks deleted, document re-processed.
- **force=true** → always re-processed regardless of ETag.

### Running Acceptance Tests

```bash
cd backend
uv run python tests/test_datalake_s3.py
```

### Common Issues – Datalake

#### "S3 list failed: … 301"
The bucket exists in a different region.  Set `AWS_REGION=ap-south-1`.

#### "Found N PDFs which exceeds the safety limit"
Raise `S3_SYNC_MAX_FILES` or narrow the prefix
(e.g. `?prefix=datalake/Invoices/`).
2. Add a bucket policy (run `configure_s3_bucket.py`)

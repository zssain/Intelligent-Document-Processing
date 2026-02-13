# Troubleshooting: Google Drive Connector

## Overview

The Google Drive connector uses the **Google Drive API v3** to list and
download PDFs from a Drive folder, then feeds them through the existing
Azure CU → normalize → chunk → embed → pgvector pipeline.

Two auth modes are supported:
1. **OAuth2 refresh token** – simplest for personal Drive or testing.
2. **Service Account** – recommended for Google Workspace with domain-wide
   delegation.

---

## Required Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GDRIVE_CLIENT_ID` | Mode 1 | OAuth2 client ID |
| `GDRIVE_CLIENT_SECRET` | Mode 1 | OAuth2 client secret |
| `GDRIVE_REFRESH_TOKEN` | Mode 1 | OAuth2 refresh token (long-lived) |
| `GDRIVE_USE_SERVICE_ACCOUNT` | Mode 2 | Set to `true` |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | Mode 2 | Path to SA key file **or** raw JSON |
| `GDRIVE_DELEGATED_USER` | Mode 2 | User email to impersonate (optional) |
| `GDRIVE_FOLDER_ID` | ✅ | Drive folder ID to list / sync |
| `GDRIVE_SYNC_MAX_FILES` | ❌ | Safety limit (default 500) |

---

## How to Get a Refresh Token (OAuth2 – Mode 1)

### Using the OAuth 2.0 Playground

1. Go to <https://developers.google.com/oauthplayground>.
2. Click the **⚙️ gear icon** (top-right) → check **Use your own OAuth
   credentials**.
3. Enter your `Client ID` and `Client Secret`.
4. On the left, find **Drive API v3** → select the scope:
   ```
   https://www.googleapis.com/auth/drive.readonly
   ```
5. Click **Authorize APIs** → sign in and grant consent.
6. Click **Exchange authorization code for tokens**.
7. Copy the **Refresh token** → set it as `GDRIVE_REFRESH_TOKEN`.

### Using the Google Cloud Console

1. Go to **Google Cloud Console** → **APIs & Services** → **Credentials**.
2. Create an **OAuth 2.0 Client ID** (type: Desktop App).
3. Download the JSON, then run a quick Python script to complete the flow:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    scopes=["https://www.googleapis.com/auth/drive.readonly"],
)
creds = flow.run_local_server(port=0)
print("Refresh token:", creds.refresh_token)
```

4. Set the printed refresh token as `GDRIVE_REFRESH_TOKEN`.

---

## Service Account Setup (Mode 2 – Google Workspace)

1. In **Google Cloud Console** → **IAM & Admin** → **Service Accounts**,
   create a new service account.
2. Create a JSON key → download it.
3. In the **Google Workspace Admin Console**
   (<https://admin.google.com>):
   - Go to **Security → API Controls → Domain-wide Delegation**.
   - Add the service account's **Client ID** with scope:
     ```
     https://www.googleapis.com/auth/drive.readonly
     ```
4. Set env vars:
   ```env
   GDRIVE_USE_SERVICE_ACCOUNT=true
   GDRIVE_SERVICE_ACCOUNT_JSON=/path/to/key.json
   GDRIVE_DELEGATED_USER=user@yourorg.com
   ```

---

## How to Find the Folder ID

Open the folder in Google Drive in a browser. The URL looks like:

```
https://drive.google.com/drive/folders/1ABCdeFGhiJKlmnOPqrSTUvwXYZ
```

The folder ID is `1ABCdeFGhiJKlmnOPqrSTUvwXYZ`.

Set it as `GDRIVE_FOLDER_ID` in your `.env`.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/datalake/gdrive/list` | List PDFs in a Drive folder |
| POST | `/api/v1/datalake/gdrive/sync` | Incrementally ingest PDFs |

### Listing PDFs

```bash
curl "http://localhost:8000/api/v1/datalake/gdrive/list?limit=20"
```

### Syncing / Ingesting

```bash
# Incremental sync (uses Changes API by default)
curl -X POST "http://localhost:8000/api/v1/datalake/gdrive/sync?limit=5"

# Full scan (ignores changes cursor, lists all children)
curl -X POST "http://localhost:8000/api/v1/datalake/gdrive/sync?full_scan=true&limit=5"

# Force re-process all files
curl -X POST "http://localhost:8000/api/v1/datalake/gdrive/sync?force=true&limit=5"

# Specify a different folder
curl -X POST "http://localhost:8000/api/v1/datalake/gdrive/sync?folder_id=1ABCdeFG&limit=5"
```

---

## Idempotency & Incremental Sync

### Source tracking

Each document is stored with `Document.source = gdrive:{file_id}`.
The file's `version` field (or `modifiedTime` fallback) is stored in
`metrics._gdrive_version`.

- **Same file_id + same version** → skipped.
- **Same file_id + different version** → old chunks deleted, re-processed.
- **force=true** → always re-processed.

### Changes cursor

The Changes API pageToken is stored in the `ingestion_cursors` table with
key `gdrive:{folder_id}`.

On the **first sync** the cursor is obtained (no items returned).
On **subsequent syncs** only files changed since the cursor are returned.

Pass `full_scan=true` to bypass the cursor and list all folder children.

---

## Running Test Scripts

```bash
cd backend

# List PDFs (direct client, no server needed)
uv run python scripts/test_gdrive_list.py

# List via the running API server
uv run python scripts/test_gdrive_list.py --via-api

# Sync test (server must be running)
uv run python scripts/test_gdrive_sync.py
```

---

## Common Issues

### "OAuth2 mode requires GDRIVE_CLIENT_ID …"

Set all three OAuth env vars, or switch to service account mode.

### "No folder_id provided and GDRIVE_FOLDER_ID is not set"

Set `GDRIVE_FOLDER_ID` in your `.env` or pass `?folder_id=…` as a query
parameter.

### 403 "Insufficient Permission"

The OAuth scope or service account delegation doesn't include
`drive.readonly`.  Re-do the auth flow with the correct scope.

### "File not found" on download

The service account / OAuth user doesn't have access to the file.
Share the folder with the service account email or ensure the OAuth
user owns / has access to the folder.

### Changes query returns 0 items on first sync

This is expected.  The first call only obtains the `startPageToken`.
On the second sync, any files that have changed since will appear.

### Token expired errors

OAuth2 refresh tokens are usually long-lived, but Google may revoke them
if the app is in "Testing" mode and 7 days have passed.  Publish the
OAuth consent screen or re-generate the token.

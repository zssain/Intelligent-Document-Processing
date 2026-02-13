# Troubleshooting: SharePoint Connector (Microsoft Graph)

## Overview

The SharePoint connector uses **Microsoft Graph API** with **app-only
(client_credentials)** authentication to list and download documents from a
SharePoint Online document library.

---

## Required Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SHAREPOINT_TENANT_ID` | ✅ | Azure AD tenant ID (GUID) |
| `SHAREPOINT_CLIENT_ID` | ✅ | App Registration client ID |
| `SHAREPOINT_CLIENT_SECRET` | ✅ | App Registration client secret |
| `SHAREPOINT_SITE_ID` | One of | Graph site ID (`host,id,id` format) |
| `SHAREPOINT_SITE_URL` | these | e.g. `yourorg.sharepoint.com:/sites/MySite` |
| `SHAREPOINT_DRIVE_ID` | ❌ | Auto-resolved from site's default library |
| `SHAREPOINT_FOLDER_PATH` | ❌ | Default: `Shared Documents/datalake` |
| `SHAREPOINT_SYNC_MAX_FILES` | ❌ | Safety limit (default 500) |

### Example `.env` block

```env
SHAREPOINT_TENANT_ID=your-tenant-id
SHAREPOINT_CLIENT_ID=your-client-id
SHAREPOINT_CLIENT_SECRET=your-client-secret
SHAREPOINT_SITE_URL=yourorg.sharepoint.com:/sites/MySite
SHAREPOINT_FOLDER_PATH=Shared Documents/datalake
```

---

## Azure AD App Registration Setup

1. Go to **Azure Portal → Azure Active Directory → App registrations**.
2. Click **New registration** → give it a name → register.
3. Under **Certificates & secrets** → add a new **Client secret**.
4. Under **API permissions** → **Add a permission** → **Microsoft Graph** →
   **Application permissions**:
   - `Sites.Read.All`
   - `Files.Read.All`
5. Click **Grant admin consent for \<tenant\>** (requires Global Admin).

> ⚠️ **Admin Consent is required.** Without it, Graph API calls will fail
> with `403 Insufficient privileges`.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/datalake/sharepoint/list` | List PDFs in a SharePoint folder |
| POST | `/api/v1/datalake/sharepoint/sync` | Incrementally ingest PDFs |

### Listing PDFs

```bash
curl "http://localhost:8000/api/v1/datalake/sharepoint/list?limit=20"
```

### Syncing / Ingesting

```bash
# Incremental sync (uses delta API by default)
curl -X POST "http://localhost:8000/api/v1/datalake/sharepoint/sync?limit=5"

# Full scan (ignores delta cursor)
curl -X POST "http://localhost:8000/api/v1/datalake/sharepoint/sync?full_scan=true&limit=5"

# Force re-process everything
curl -X POST "http://localhost:8000/api/v1/datalake/sharepoint/sync?force=true&limit=5"
```

---

## Idempotency & Delta Sync

### Source tracking

Each document is stored with `Document.source = sharepoint:{drive_id}:{item_id}`.
The Graph eTag is stored in `metrics._sp_etag`.

- **Same item_id + same eTag** → skipped.
- **Same item_id + different eTag** → old chunks deleted, re-processed.
- **force=true** → always re-processed.

### Delta cursor

The delta cursor (deltaLink) is stored in the `ingestion_cursors` table with
key `sharepoint:{site_id}:{drive_id}:{folder_path}`.  On subsequent syncs
only items that changed since the last sync are returned by Graph.

Pass `full_scan=true` to bypass the delta cursor and enumerate all children.

---

## Folder Path Format

The `SHAREPOINT_FOLDER_PATH` should be the **relative path inside the
document library drive**.  Examples:

| What you want | Value |
|---|---|
| Root of default library | `""` (empty) |
| Standard "Documents" root | `Shared Documents` |
| Datalake sub-folder | `Shared Documents/datalake` |
| Invoices sub-folder | `Shared Documents/datalake/Invoices` |

---

## Running Acceptance Tests

```bash
cd backend

# Quick list test
uv run python scripts/test_sharepoint_list.py

# Sync test (needs all pipeline services running)
uv run python scripts/test_sharepoint_sync.py
```

---

## Common Issues

### 403 Insufficient privileges

Admin Consent has not been granted for the required permissions.
Go to Azure Portal → App registrations → API permissions → Grant admin consent.

### "Cannot resolve site_id: neither SHAREPOINT_SITE_ID nor SHAREPOINT_SITE_URL is set"

Set one of `SHAREPOINT_SITE_ID` or `SHAREPOINT_SITE_URL` in your `.env`.

### "Token request failed (401)"

Check that `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, and
`SHAREPOINT_CLIENT_SECRET` are correct and the secret has not expired.

### Delta query returns all items on first run

This is expected.  The first delta call returns the full set and a
deltaLink.  Subsequent calls will return only changes.

### "SharePoint list failed: … 404"

The folder path does not exist or is misspelled.  Double-check
`SHAREPOINT_FOLDER_PATH` matches the actual folder structure in SharePoint.

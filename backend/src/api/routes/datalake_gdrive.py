"""Google Drive datalake endpoints – list & incremental sync.

These endpoints mirror the S3 and SharePoint datalake endpoints but pull
documents from a Google Drive folder instead.

Auth
----
Uses **per-user OAuth tokens** stored in Firestore
(``tenants/{tenant}/user_connections/{uid}``).  The user must first
connect via ``/auth/gdrive/connect``.  When no user tokens are available
the endpoint falls back to org-level credentials
(``GDRIVE_CLIENT_ID``/``GDRIVE_REFRESH_TOKEN``).

Folder resolution
-----------------
If ``folder_id`` is not supplied as a query parameter, the endpoint looks
up the user's linked source connections in Firestore
(``tenants/{tenant}/source_connections``).

Idempotency
-----------
Each Drive file is tracked via ``Document.source`` using the format
``gdrive:{file_id}``.  The Drive ``version`` field (or ``modifiedTime`` as
fallback) is stored in ``metrics._gdrive_version``.  When the same file_id
reappears with a different version the old chunks are deleted and the
Document row is updated in-place.

Changes API
-----------
By default the ``/sync`` endpoint uses the Google Drive Changes API which
returns only items modified since the last call.  A cursor (pageToken) is
persisted in the ``ingestion_cursors`` table.

Pass ``full_scan=true`` to ignore the cursor and list all folder children.

Safety
------
* ``gdrive_sync_max_files`` (default 500) prevents runaway ingestion.
* Each file is processed in isolation – one bad PDF does not stop the sync.
* Per-file DB rollback on failure.
* Retry with exponential back-off for CU & embedding calls (3 attempts).
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.settings import settings, DEFAULT_TENANT_ID
from src.connectors.google_drive import (
    GoogleDriveClient,
    GDriveAuthError,
    GDriveAPIError,
)
from src.database.base import get_db
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from src.processing import process_document
from src.storage.s3_service import S3Service
from src.api.auth import CurrentUser, get_current_user, require_source_permission

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_s3: Optional[S3Service] = None


def _get_s3() -> Optional[S3Service]:
    global _s3
    if _s3 is None:
        try:
            _s3 = S3Service()
        except Exception as exc:
            logger.warning("S3 not available for artifact upload: %s", exc)
    return _s3


# ---------------------------------------------------------------------------
# Per-user Google Drive client helpers
# ---------------------------------------------------------------------------

def _get_user_tokens(tenant_id: str, uid: str) -> Optional[Dict]:
    """Load decrypted OAuth tokens for the user from Firestore."""
    try:
        from src.api.routes.oauth import _decrypt
        from src.utils.firebase import get_firestore_client

        db = get_firestore_client()
        doc_ref = (
            db.collection("tenants")
            .document(tenant_id)
            .collection("user_connections")
            .document(uid)
        )
        doc = doc_ref.get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        gdrive = data.get("gdrive")
        if not gdrive or gdrive.get("status") != "connected":
            return None

        return {
            "access_token": _decrypt(gdrive["encrypted_access_token"]),
            "refresh_token": _decrypt(gdrive.get("encrypted_refresh_token", "")),
        }
    except Exception as exc:
        logger.warning("Could not load user tokens: %s", exc)
        return None


def _build_user_gdrive_client(user_tokens: Optional[Dict] = None) -> GoogleDriveClient:
    """Build a GoogleDriveClient using per-user tokens or fall back to org-level."""
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from googleapiclient.discovery import build as build_service

    if user_tokens and user_tokens.get("access_token"):
        creds = OAuthCredentials(
            token=user_tokens["access_token"],
            refresh_token=user_tokens.get("refresh_token"),
            client_id=settings.gdrive_oauth_client_id or settings.gdrive_client_id,
            client_secret=settings.gdrive_oauth_client_secret or settings.gdrive_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        client = GoogleDriveClient.__new__(GoogleDriveClient)
        client._service = build_service("drive", "v3", credentials=creds)
        logger.info("Built per-user GoogleDriveClient")
        return client

    # Fall back to org-level credentials
    return GoogleDriveClient()


def _resolve_folder_id(tenant_id: str, uid: str, folder_id: Optional[str]) -> Optional[str]:
    """Return an effective folder_id - either from the query param, linked
    source connections in Firestore, or the settings default."""
    if folder_id:
        return folder_id

    # Check linked source connections
    try:
        from src.utils.firebase import get_firestore_client
        db = get_firestore_client()
        coll = (
            db.collection("tenants")
            .document(tenant_id)
            .collection("source_connections")
        )
        for doc in coll.where("provider", "==", "gdrive").stream():
            d = doc.to_dict()
            fid = d.get("folder_id")
            if fid and d.get("status") == "connected":
                logger.info("Resolved folder_id=%s from linked connection %s", fid, doc.id)
                return fid
    except Exception as exc:
        logger.warning("Could not resolve folder from source connections: %s", exc)

    return settings.gdrive_folder_id or None



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _source_key(file_id: str) -> str:
    """Deterministic source identifier for a Drive file."""
    return f"gdrive:{file_id}"


def _version_tag(item: dict) -> str:
    """Pick the best version marker from a Drive file metadata dict.

    Prefers ``version`` (int), falls back to ``modifiedTime``.
    """
    return str(item.get("version") or item.get("modifiedTime") or "")


def _cursor_key(folder_id: str) -> str:
    return f"gdrive:{folder_id}"


def _load_cursor(firestore_svc: FirestoreService, key: str) -> Optional[str]:
    cursor = firestore_svc.get_cursor(key)
    return cursor["cursor_value"] if cursor else None


def _save_cursor(firestore_svc: FirestoreService, key: str, value: str) -> None:
    firestore_svc.set_cursor(key, "gdrive", value)


# ---------------------------------------------------------------------------
# GET /gdrive/list
# ---------------------------------------------------------------------------
@router.get("/gdrive/list", dependencies=[Depends(require_source_permission("gdrive", "can_view"))])
async def list_gdrive_pdfs(
    folder_id: str = Query(
        default=None,
        description="Google Drive folder ID (default from linked connections)",
    ),
    limit: int = Query(default=100, ge=1, le=5000),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List PDF files in a Google Drive folder."""
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    uid = current_user.uid

    effective_folder = _resolve_folder_id(tenant_id, uid, folder_id)

    # Try per-user tokens first
    user_tokens = _get_user_tokens(tenant_id, uid)
    has_user_tokens = user_tokens and user_tokens.get("access_token")
    has_org_oauth = settings.gdrive_client_id and settings.gdrive_refresh_token
    has_sa = settings.gdrive_use_service_account and settings.gdrive_service_account_json

    if not effective_folder or (not has_user_tokens and not has_org_oauth and not has_sa):
        return {
            "folder_id": effective_folder or "",
            "total_files": 0,
            "files": [],
            "_note": (
                "Google Drive connector is not configured. "
                "Connect your Google account first, then link a folder via Connect via Link."
            ),
        }

    try:
        gdrive = _build_user_gdrive_client(user_tokens)
        items = gdrive.list_folder_files(
            effective_folder,
            limit=limit,
            supported_extensions=settings.supported_extensions,
        )
    except Exception as exc:
        logger.warning("Google Drive list failed: %s", exc)
        return {
            "folder_id": effective_folder,
            "total_files": 0,
            "files": [],
            "_note": f"Google Drive list failed: {exc}",
        }

    pdfs = []
    for item in items:
        pdfs.append({
            "name": item.get("name", ""),
            "file_id": item["id"],
            "webViewLink": item.get("webViewLink", ""),
            "size": int(item.get("size", 0)),
            "modifiedTime": item.get("modifiedTime", ""),
            "md5Checksum": item.get("md5Checksum", ""),
            "version": item.get("version", ""),
        })

    return {
        "folder_id": effective_folder,
        "total_files": len(pdfs),
        "files": pdfs,
    }


# ---------------------------------------------------------------------------
# POST /gdrive/sync
# ---------------------------------------------------------------------------
@router.post("/gdrive/sync", dependencies=[Depends(require_source_permission("gdrive", "can_sync"))])
async def sync_gdrive(
    folder_id: str = Query(default=None, description="Drive folder ID to sync"),
    limit: int = Query(default=None, ge=1, description="Max PDFs to process"),
    force: bool = Query(default=False, description="Re-process even if already ingested"),
    full_scan: bool = Query(
        default=False,
        description="Ignore changes cursor and list all children (slower)",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Incrementally ingest PDFs from a Google Drive folder.

    Uses the Drive Changes API by default so only modified items are
    returned on subsequent calls.  Authenticates using the current
    user's per-user OAuth tokens.
    """
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    uid = current_user.uid

    effective_folder = _resolve_folder_id(tenant_id, uid, folder_id)
    user_tokens = _get_user_tokens(tenant_id, uid)
    has_user_tokens = user_tokens and user_tokens.get("access_token")
    has_org_oauth = settings.gdrive_client_id and settings.gdrive_refresh_token
    has_sa = settings.gdrive_use_service_account and settings.gdrive_service_account_json

    if not effective_folder or (not has_user_tokens and not has_org_oauth and not has_sa):
        return {
            "status": "skipped",
            "total_files": 0, "ingested": 0, "updated": 0, "skipped": 0, "failed": 0,
            "_note": "Google Drive connector is not configured. Connect your Google account and link a folder.",
        }
    effective_limit = limit or settings.gdrive_sync_max_files

    logger.info(
        "▶ Google Drive sync started – folder=%s, limit=%d, force=%s, full_scan=%s, user=%s",
        effective_folder, effective_limit, force, full_scan, uid,
    )

    # 1. Build client -------------------------------------------------------
    try:
        gdrive = _build_user_gdrive_client(user_tokens)
    except (GDriveAuthError, GDriveAPIError) as exc:
        logger.error("Google Drive auth failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Firestore service for idempotency + cursors
    firestore_svc = FirestoreService(tenant_id=tenant_id)

    # 2. Get items -----------------------------------------------------------
    ck = _cursor_key(effective_folder)
    used_changes = False
    new_page_token: Optional[str] = None

    try:
        if full_scan:
            items = gdrive.list_folder_files(
                effective_folder,
                limit=effective_limit,
                supported_extensions=settings.supported_extensions,
            )
        else:
            stored_token = _load_cursor(firestore_svc, ck)
            items, new_page_token = gdrive.changes_query(
                effective_folder,
                page_token=stored_token,
                max_items=effective_limit,
                supported_extensions=settings.supported_extensions,
            )
            used_changes = stored_token is not None
    except Exception as exc:
        logger.error("Google Drive query failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Safety guard
    if len(items) > settings.gdrive_sync_max_files:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Found {len(items)} PDFs which exceeds the safety limit of "
                f"{settings.gdrive_sync_max_files}. Narrow the folder or raise "
                "GDRIVE_SYNC_MAX_FILES."
            ),
        )

    ingested = 0
    skipped = 0
    updated = 0
    failed = 0
    errors: list[dict] = []

    for item in items:
        file_id: str = item["id"]
        file_name: str = item.get("name", file_id)
        file_version: str = _version_tag(item)
        file_size: int = int(item.get("size", 0))
        web_link: str = item.get("webViewLink", "")
        md5: str = item.get("md5Checksum", "")
        src_key = _source_key(file_id)

        tmp_path: Optional[str] = None
        try:
            # 3. Idempotency check via Firestore ----------------------------
            existing = firestore_svc.get_document_by_source(
                source_type="gdrive",
                source_key="_gdrive_file_id",
                source_value=file_id,
            )

            if existing and not force:
                stored_ver = existing.get("stats", {}).get("_gdrive_version")
                if stored_ver == file_version:
                    logger.debug("SKIP (unchanged) %s", file_name)
                    skipped += 1
                    continue
                logger.info(
                    "Version changed for %s (old=%s new=%s) – re-processing",
                    file_name, stored_ver, file_version,
                )

            if existing and force:
                logger.info("FORCE re-process %s", file_name)

            # 4. Download ---------------------------------------------------
            tmp_path = gdrive.download_file(file_id, filename=file_name)

            # 4b. Upload PDF to S3 for preview/download ----------------------
            s3_pdf_url = None
            _s3 = _get_s3()
            if _s3:
                try:
                    s3_pdf_url = _s3.upload_pdf(tmp_path, file_name)
                    logger.info("Uploaded GDrive PDF to S3: %s", s3_pdf_url)
                except Exception as s3_exc:
                    logger.warning(
                        "S3 upload of GDrive PDF failed (non-fatal): %s", s3_exc
                    )

            # 5-11. Centralized pipeline ------------------------------------
            result = process_document(
                file_path=tmp_path,
                filename=file_name,
                db=db,
                tenant_id=DEFAULT_TENANT_ID,
                s3_service=_s3,
                s3_url=s3_pdf_url or web_link,
                file_size_bytes=file_size,
                source="gdrive",
                source_metadata={
                    "_gdrive_file_id": file_id,
                    "_gdrive_md5": md5,
                    "_gdrive_web_link": web_link,
                    "source_key": src_key,
                },
                extra_metrics={
                    "_gdrive_version": file_version,
                    "_gdrive_file_id": file_id,
                    "_gdrive_md5": md5,
                    "_gdrive_web_link": web_link,
                },
                existing_doc_id=existing["id"] if existing else None,
            )

            db.commit()

            if existing:
                updated += 1
                logger.info("UPDATED document %s for %s", result.document_id, file_name)
            else:
                ingested += 1
                logger.info("INGESTED document %s for %s", result.document_id, file_name)

        except Exception as exc:
            db.rollback()
            failed += 1
            err_msg = f"{type(exc).__name__}: {exc}"
            errors.append({"file": file_name, "file_id": file_id, "error": err_msg})
            logger.error("FAILED to process %s: %s", file_name, err_msg, exc_info=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # 12. Persist changes cursor --------------------------------------------
    if new_page_token:
        try:
            _save_cursor(firestore_svc, ck, new_page_token)
            logger.info("Changes cursor saved for %s", ck)
        except Exception as exc:
            logger.warning("Failed to save changes cursor: %s", exc)

    summary = {
        "status": "completed",
        "folder_id": effective_folder,
        "total_files": len(items),
        "ingested": ingested,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "used_changes": used_changes,
        "cursor_key": ck,
    }
    if errors:
        summary["errors"] = errors

    logger.info("▶ Google Drive sync finished – %s", summary)
    return summary

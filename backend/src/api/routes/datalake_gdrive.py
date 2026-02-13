"""Google Drive datalake endpoints – list & incremental sync.

These endpoints mirror the S3 and SharePoint datalake endpoints but pull
documents from a Google Drive folder instead.

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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session

from config.settings import settings
from src.connectors.google_drive import (
    GoogleDriveClient,
    GDriveAuthError,
    GDriveAPIError,
)
from src.database.base import get_db
from src.database.models import Document, IngestionCursor
from src.processing import process_document
from src.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy singletons (consistent with datalake_s3 / datalake_sharepoint)
# ---------------------------------------------------------------------------
_gdrive: Optional[GoogleDriveClient] = None
_s3: Optional[S3Service] = None


def _get_gdrive() -> GoogleDriveClient:
    global _gdrive
    if _gdrive is None:
        _gdrive = GoogleDriveClient()
    return _gdrive


def _get_s3() -> Optional[S3Service]:
    global _s3
    if _s3 is None:
        try:
            _s3 = S3Service()
        except Exception as exc:
            logger.warning("S3 not available for artifact upload: %s", exc)
    return _s3


# ---------------------------------------------------------------------------
# Auth guard (reuse pattern from S3 / SharePoint routers)
# ---------------------------------------------------------------------------
def _verify_api_key(x_api_key: str = Header(default="")) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


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


def _load_cursor(db: Session, key: str) -> Optional[str]:
    row = db.query(IngestionCursor).filter(IngestionCursor.cursor_key == key).first()
    return row.cursor_value if row else None


def _save_cursor(db: Session, key: str, value: str) -> None:
    row = db.query(IngestionCursor).filter(IngestionCursor.cursor_key == key).first()
    if row:
        row.cursor_value = value
    else:
        row = IngestionCursor(provider="gdrive", cursor_key=key, cursor_value=value)
        db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# GET /gdrive/list
# ---------------------------------------------------------------------------
@router.get("/gdrive/list", dependencies=[Depends(_verify_api_key)])
async def list_gdrive_pdfs(
    folder_id: str = Query(
        default=None,
        description="Google Drive folder ID (default from settings)",
    ),
    limit: int = Query(default=100, ge=1, le=5000),
):
    """List PDF files in a Google Drive folder."""
    effective_folder = folder_id or settings.gdrive_folder_id

    # Early exit when Google Drive is not configured
    has_oauth = settings.gdrive_client_id and settings.gdrive_refresh_token
    has_sa = settings.gdrive_use_service_account and settings.gdrive_service_account_json
    if not effective_folder or (not has_oauth and not has_sa):
        return {
            "folder_id": effective_folder or "",
            "total_pdfs": 0,
            "pdfs": [],
            "_note": "Google Drive connector is not configured. Set GDRIVE_FOLDER_ID and authentication credentials.",
        }

    try:
        gdrive = _get_gdrive()
        items = gdrive.list_folder_pdfs(effective_folder, limit=limit)
    except Exception as exc:
        logger.warning("Google Drive list failed: %s", exc)
        return {
            "folder_id": effective_folder,
            "total_pdfs": 0,
            "pdfs": [],
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
        "total_pdfs": len(pdfs),
        "pdfs": pdfs,
    }


# ---------------------------------------------------------------------------
# POST /gdrive/sync
# ---------------------------------------------------------------------------
@router.post("/gdrive/sync", dependencies=[Depends(_verify_api_key)])
async def sync_gdrive(
    folder_id: str = Query(default=None, description="Drive folder ID to sync"),
    limit: int = Query(default=None, ge=1, description="Max PDFs to process"),
    force: bool = Query(default=False, description="Re-process even if already ingested"),
    full_scan: bool = Query(
        default=False,
        description="Ignore changes cursor and list all children (slower)",
    ),
    db: Session = Depends(get_db),
):
    """Incrementally ingest PDFs from a Google Drive folder.

    Uses the Drive Changes API by default so only modified items are
    returned on subsequent calls.
    """
    effective_folder = folder_id or settings.gdrive_folder_id
    has_oauth = settings.gdrive_client_id and settings.gdrive_refresh_token
    has_sa = settings.gdrive_use_service_account and settings.gdrive_service_account_json
    if not effective_folder or (not has_oauth and not has_sa):
        return {
            "status": "skipped",
            "total_pdfs": 0, "ingested": 0, "updated": 0, "skipped": 0, "failed": 0,
            "_note": "Google Drive connector is not configured.",
        }
    effective_limit = limit or settings.gdrive_sync_max_files

    logger.info(
        "▶ Google Drive sync started – folder=%s, limit=%d, force=%s, full_scan=%s",
        effective_folder, effective_limit, force, full_scan,
    )

    # 1. Build client -------------------------------------------------------
    try:
        gdrive = _get_gdrive()
    except (GDriveAuthError, GDriveAPIError) as exc:
        logger.error("Google Drive auth failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 2. Get items -----------------------------------------------------------
    ck = _cursor_key(effective_folder)
    used_changes = False
    new_page_token: Optional[str] = None

    try:
        if full_scan:
            items = gdrive.list_folder_pdfs(effective_folder, limit=effective_limit)
        else:
            stored_token = _load_cursor(db, ck)
            items, new_page_token = gdrive.changes_query(
                effective_folder,
                page_token=stored_token,
                max_items=effective_limit,
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
            # 3. Idempotency check ------------------------------------------
            existing: Optional[Document] = (
                db.query(Document).filter(Document.source == src_key).first()
            )

            if existing and not force:
                stored_ver = (existing.metrics or {}).get("_gdrive_version")
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
            tmp_path = gdrive.download_file(file_id)

            # 5-11. Centralized pipeline ------------------------------------
            result = process_document(
                file_path=tmp_path,
                filename=file_name,
                db=db,
                s3_service=_get_s3(),
                s3_url=web_link,
                file_size_bytes=file_size,
                source=src_key,
                extra_metrics={
                    "_gdrive_version": file_version,
                    "_gdrive_file_id": file_id,
                    "_gdrive_md5": md5,
                    "_gdrive_web_link": web_link,
                },
                existing_doc=existing,
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
            _save_cursor(db, ck, new_page_token)
            logger.info("Changes cursor saved for %s", ck)
        except Exception as exc:
            logger.warning("Failed to save changes cursor: %s", exc)

    summary = {
        "status": "completed",
        "folder_id": effective_folder,
        "total_pdfs": len(items),
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

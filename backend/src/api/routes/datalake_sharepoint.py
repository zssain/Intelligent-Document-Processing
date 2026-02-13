"""SharePoint datalake endpoints – list & incremental sync via Microsoft Graph.

These endpoints mirror the S3 datalake endpoints but pull documents from a
SharePoint Online document library instead.

Idempotency
-----------
Each SharePoint item is tracked via ``Document.source`` using the format
``sharepoint:{drive_id}:{item_id}``.  The Graph eTag is stored in
``metrics._sp_etag``.  When the same item_id reappears with a different eTag
(i.e. the file was edited/replaced) the old chunks are deleted and the
Document row is updated in-place.

Delta API
---------
By default the ``/sync`` endpoint uses Microsoft Graph's delta query which
returns only items that changed since the last call.  A cursor (deltaLink) is
persisted in the ``ingestion_cursors`` table so subsequent syncs are
near-instant if nothing changed.

Pass ``full_scan=true`` to ignore the delta cursor and list all children.

Safety
------
* ``sharepoint_sync_max_files`` (default 500) prevents runaway ingestion.
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
from src.connectors.sharepoint_graph import GraphClient, GraphAuthError, GraphAPIError
from src.database.base import get_db
from src.database.models import Document, IngestionCursor
from src.processing import process_document
from src.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_graph: Optional[GraphClient] = None
_s3: Optional[S3Service] = None


def _get_graph() -> GraphClient:
    global _graph
    if _graph is None:
        _graph = GraphClient()
    return _graph


def _get_s3() -> Optional[S3Service]:
    global _s3
    if _s3 is None:
        try:
            _s3 = S3Service()
        except Exception as exc:
            logger.warning("S3 not available for artifact upload: %s", exc)
    return _s3


# ---------------------------------------------------------------------------
# Auth guard (same pattern as datalake_s3)
# ---------------------------------------------------------------------------
def _verify_api_key(x_api_key: str = Header(default="")) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _source_key(drive_id: str, item_id: str) -> str:
    """Deterministic source identifier for a SharePoint item."""
    return f"sharepoint:{drive_id}:{item_id}"


def _cursor_key(site_id: str, drive_id: str, folder_path: str) -> str:
    return f"sharepoint:{site_id}:{drive_id}:{folder_path}"


def _is_pdf(item: dict) -> bool:
    name: str = item.get("name", "")
    return name.lower().endswith(".pdf") and "file" in item


def _load_cursor(db: Session, key: str) -> Optional[str]:
    row = db.query(IngestionCursor).filter(IngestionCursor.cursor_key == key).first()
    return row.cursor_value if row else None


def _save_cursor(db: Session, key: str, value: str) -> None:
    row = db.query(IngestionCursor).filter(IngestionCursor.cursor_key == key).first()
    if row:
        row.cursor_value = value
    else:
        row = IngestionCursor(provider="sharepoint", cursor_key=key, cursor_value=value)
        db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# GET /sharepoint/list
# ---------------------------------------------------------------------------
@router.get("/sharepoint/list", dependencies=[Depends(_verify_api_key)])
async def list_sharepoint_pdfs(
    folder_path: str = Query(
        default=None,
        description="Folder path inside the document library (default from settings)",
    ),
    limit: int = Query(default=100, ge=1, le=5000),
):
    """List PDF items in a SharePoint folder."""
    # Early exit when SharePoint is not fully configured
    missing_creds = (
        not settings.sharepoint_tenant_id
        or not settings.sharepoint_client_id
        or not settings.sharepoint_client_secret
    )
    missing_site = not settings.sharepoint_site_id and not settings.sharepoint_site_url
    if missing_creds or missing_site:
        return {
            "folder_path": folder_path or settings.sharepoint_folder_path,
            "drive_id": "",
            "total_items": 0,
            "total_pdfs": 0,
            "pdfs": [],
            "_note": "SharePoint connector is not configured. Set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET and either SHAREPOINT_SITE_ID or SHAREPOINT_SITE_URL.",
        }

    effective_path = folder_path or settings.sharepoint_folder_path
    try:
        graph = _get_graph()
        _site_id, drive_id = graph.get_site_and_drive()
        items = graph.list_folder_children(drive_id, effective_path, max_items=limit)
    except Exception as exc:
        logger.warning("SharePoint list failed: %s", exc)
        return {
            "folder_path": effective_path,
            "drive_id": "",
            "total_items": 0,
            "total_pdfs": 0,
            "pdfs": [],
            "_note": f"SharePoint list failed: {exc}",
        }

    pdfs = []
    for item in items:
        if not _is_pdf(item):
            continue
        pdfs.append({
            "name": item["name"],
            "item_id": item["id"],
            "webUrl": item.get("webUrl", ""),
            "size": item.get("size", 0),
            "lastModifiedDateTime": item.get("lastModifiedDateTime", ""),
            "eTag": item.get("eTag", ""),
        })

    return {
        "folder_path": effective_path,
        "drive_id": drive_id,
        "total_items": len(items),
        "total_pdfs": len(pdfs),
        "pdfs": pdfs,
    }


# ---------------------------------------------------------------------------
# POST /sharepoint/sync
# ---------------------------------------------------------------------------
@router.post("/sharepoint/sync", dependencies=[Depends(_verify_api_key)])
async def sync_sharepoint(
    folder_path: str = Query(default=None, description="Folder path to sync"),
    limit: int = Query(default=None, ge=1, description="Max PDFs to process"),
    force: bool = Query(default=False, description="Re-process even if already ingested"),
    full_scan: bool = Query(
        default=False,
        description="Ignore delta cursor and list all children (slower)",
    ),
    db: Session = Depends(get_db),
):
    """Incrementally ingest PDFs from a SharePoint folder.

    Uses Microsoft Graph delta API by default so only changed items are
    returned on subsequent calls.
    """
    # Early exit when not configured
    missing_creds = (
        not settings.sharepoint_tenant_id
        or not settings.sharepoint_client_id
        or not settings.sharepoint_client_secret
    )
    missing_site = not settings.sharepoint_site_id and not settings.sharepoint_site_url
    if missing_creds or missing_site:
        return {
            "status": "skipped",
            "total_pdfs": 0, "ingested": 0, "updated": 0, "skipped": 0, "failed": 0,
            "_note": "SharePoint connector is not configured.",
        }

    effective_path = folder_path or settings.sharepoint_folder_path
    effective_limit = limit or settings.sharepoint_sync_max_files

    logger.info(
        "▶ SharePoint sync started – folder=%s, limit=%d, force=%s, full_scan=%s",
        effective_path, effective_limit, force, full_scan,
    )

    # 1. Resolve IDs --------------------------------------------------------
    try:
        graph = _get_graph()
        site_id, drive_id = graph.get_site_and_drive()
    except (GraphAuthError, GraphAPIError) as exc:
        logger.error("SharePoint auth / resolve failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 2. Get items -----------------------------------------------------------
    ck = _cursor_key(site_id, drive_id, effective_path)
    used_delta = False
    new_delta_link: Optional[str] = None

    try:
        if full_scan:
            items = graph.list_folder_children(
                drive_id, effective_path, max_items=effective_limit
            )
        else:
            delta_link = _load_cursor(db, ck)
            items, new_delta_link = graph.delta_query(
                drive_id, effective_path,
                delta_link=delta_link,
                max_items=effective_limit,
            )
            used_delta = delta_link is not None
    except (GraphAuthError, GraphAPIError) as exc:
        logger.error("SharePoint query failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    pdfs = [i for i in items if _is_pdf(i)]

    # Safety guard
    if len(pdfs) > settings.sharepoint_sync_max_files:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Found {len(pdfs)} PDFs which exceeds the safety limit of "
                f"{settings.sharepoint_sync_max_files}. Narrow the folder or "
                "raise SHAREPOINT_SYNC_MAX_FILES."
            ),
        )

    ingested = 0
    skipped = 0
    updated = 0
    failed = 0
    errors: list[dict] = []

    for item in pdfs:
        item_id: str = item["id"]
        item_name: str = item["name"]
        item_etag: str = item.get("eTag", "")
        item_size: int = item.get("size", 0)
        web_url: str = item.get("webUrl", "")
        src_key = _source_key(drive_id, item_id)

        tmp_path: Optional[str] = None
        try:
            # 3. Idempotency check ------------------------------------------
            existing: Optional[Document] = (
                db.query(Document).filter(Document.source == src_key).first()
            )

            if existing and not force:
                stored_etag = (existing.metrics or {}).get("_sp_etag")
                if stored_etag == item_etag:
                    logger.debug("SKIP (unchanged) %s", item_name)
                    skipped += 1
                    continue
                logger.info(
                    "eTag changed for %s – re-processing", item_name
                )

            if existing and force:
                logger.info("FORCE re-process %s", item_name)

            # 4. Download ---------------------------------------------------
            tmp_path = graph.download_file(drive_id, item_id)

            # 5-11. Centralized pipeline ------------------------------------
            result = process_document(
                file_path=tmp_path,
                filename=item_name,
                db=db,
                s3_service=_get_s3(),
                s3_url=web_url,
                file_size_bytes=item_size,
                source=src_key,
                extra_metrics={
                    "_sp_etag": item_etag,
                    "_sp_item_id": item_id,
                    "_sp_drive_id": drive_id,
                    "_sp_web_url": web_url,
                },
                existing_doc=existing,
            )

            db.commit()

            if existing:
                updated += 1
                logger.info("UPDATED document %s for %s", result.document_id, item_name)
            else:
                ingested += 1
                logger.info("INGESTED document %s for %s", result.document_id, item_name)

        except Exception as exc:
            db.rollback()
            failed += 1
            err_msg = f"{type(exc).__name__}: {exc}"
            errors.append({"item": item_name, "item_id": item_id, "error": err_msg})
            logger.error("FAILED to process %s: %s", item_name, err_msg, exc_info=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # 12. Persist delta cursor ----------------------------------------------
    if new_delta_link:
        try:
            _save_cursor(db, ck, new_delta_link)
            logger.info("Delta cursor saved for %s", ck)
        except Exception as exc:
            logger.warning("Failed to save delta cursor: %s", exc)

    summary = {
        "status": "completed",
        "folder_path": effective_path,
        "drive_id": drive_id,
        "total_pdfs": len(pdfs),
        "ingested": ingested,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "used_delta": used_delta,
        "cursor_key": ck,
    }
    if errors:
        summary["errors"] = errors

    logger.info("▶ SharePoint sync finished – %s", summary)
    return summary

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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.settings import settings, DEFAULT_TENANT_ID
from src.connectors.sharepoint_graph import GraphClient, GraphAuthError, GraphAPIError
from src.database.base import get_db
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from src.api.auth import CurrentUser, get_current_user
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
# Connection resolution from Firestore source_connections
# ---------------------------------------------------------------------------

def _resolve_sharepoint_connection(tenant_id: str):
    """Resolve SharePoint site info from Firestore linked connections.
    
    Returns (site_hostname, site_path, folder_path) or (None, None, None)
    if no linked connection found.
    """
    try:
        from src.utils.firebase import get_firestore_client
        db = get_firestore_client()
        coll = (
            db.collection("tenants")
            .document(tenant_id)
            .collection("source_connections")
        )
        for doc in coll.where("provider", "==", "sharepoint").stream():
            d = doc.to_dict()
            if d.get("status") == "connected":
                hostname = d.get("site_hostname")
                site_path = d.get("site_path")
                item_path = d.get("item_path")
                if hostname and site_path:
                    logger.info(
                        "Resolved SharePoint connection %s → %s%s (folder=%s)",
                        doc.id, hostname, site_path, item_path,
                    )
                    return hostname, site_path, item_path
    except Exception as exc:
        logger.warning("Could not resolve SharePoint from source connections: %s", exc)
    return None, None, None


def _build_graph_for_connection(site_hostname: str, site_path: str):
    """Build a GraphClient and resolve site → drive for a linked connection."""
    graph = GraphClient()
    site_url = f"{site_hostname}:{site_path}"
    site_id = graph.resolve_site_id(site_url)
    drive_id = graph.resolve_drive_id(site_id)
    return graph, site_id, drive_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _source_key(drive_id: str, item_id: str) -> str:
    """Deterministic source identifier for a SharePoint item."""
    return f"sharepoint:{drive_id}:{item_id}"


def _cursor_key(site_id: str, drive_id: str, folder_path: str) -> str:
    return f"sharepoint:{site_id}:{drive_id}:{folder_path}"


def _is_supported(item: dict) -> bool:
    name: str = item.get("name", "")
    ext = os.path.splitext(name)[1].lstrip(".").lower()
    return ext in settings.supported_extensions and "file" in item


def _load_cursor(firestore_svc: FirestoreService, key: str) -> Optional[str]:
    cursor = firestore_svc.get_cursor(key)
    return cursor["cursor_value"] if cursor else None


def _save_cursor(firestore_svc: FirestoreService, key: str, value: str) -> None:
    firestore_svc.set_cursor(key, "sharepoint", value)


# ---------------------------------------------------------------------------
# GET /sharepoint/list
# ---------------------------------------------------------------------------
@router.get("/sharepoint/list")
async def list_sharepoint_pdfs(
    folder_path: str = Query(
        default=None,
        description="Folder path inside the document library (default from settings)",
    ),
    limit: int = Query(default=100, ge=1, le=5000),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List PDF items in a SharePoint folder."""
    # Early exit when SharePoint is not fully configured
    missing_creds = (
        not settings.sharepoint_tenant_id
        or not settings.sharepoint_client_id
        or not settings.sharepoint_client_secret
    )
    if missing_creds:
        return {
            "folder_path": folder_path or settings.sharepoint_folder_path,
            "drive_id": "",
            "total_items": 0,
            "total_files": 0,
            "files": [],
            "_note": "SharePoint connector is not configured. Set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET.",
        }

    # Resolve site info: prefer env vars, fall back to linked connections
    missing_site = not settings.sharepoint_site_id and not settings.sharepoint_site_url
    use_connection = False
    conn_hostname = conn_site_path = conn_item_path = None
    if missing_site:
        tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
        conn_hostname, conn_site_path, conn_item_path = _resolve_sharepoint_connection(tenant_id)
        if not conn_hostname:
            return {
                "folder_path": folder_path or settings.sharepoint_folder_path,
                "drive_id": "",
                "total_items": 0,
                "total_files": 0,
                "files": [],
                "_note": "No SharePoint site configured. Connect a SharePoint folder via 'Connect via Link' or set SHAREPOINT_SITE_URL.",
            }
        use_connection = True

    try:
        if use_connection:
            graph, _site_id, drive_id = _build_graph_for_connection(
                conn_hostname, conn_site_path
            )
            effective_path = folder_path or conn_item_path  # None → drive root
        else:
            graph = _get_graph()
            _site_id, drive_id = graph.get_site_and_drive()
            effective_path = folder_path or settings.sharepoint_folder_path
        # Recursively list files inside subfolders
        items = graph.list_all_files_recursive(drive_id, effective_path, max_files=limit)
    except Exception as exc:
        logger.warning("SharePoint list failed: %s", exc)
        effective_path = folder_path or (conn_item_path if use_connection else settings.sharepoint_folder_path) or ""
        return {
            "folder_path": effective_path,
            "drive_id": "",
            "total_items": 0,
            "total_files": 0,
            "files": [],
            "_note": f"SharePoint list failed: {exc}",
        }

    pdfs = []
    for item in items:
        if not _is_supported(item):
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
        "total_files": len(pdfs),
        "files": pdfs,
    }


# ---------------------------------------------------------------------------
# POST /sharepoint/sync
# ---------------------------------------------------------------------------
@router.post("/sharepoint/sync")
async def sync_sharepoint(
    folder_path: str = Query(default=None, description="Folder path to sync"),
    limit: int = Query(default=None, ge=1, description="Max PDFs to process"),
    force: bool = Query(default=False, description="Re-process even if already ingested"),
    full_scan: bool = Query(
        default=False,
        description="Ignore delta cursor and list all children (slower)",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
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
    if missing_creds:
        return {
            "status": "skipped",
            "total_files": 0, "ingested": 0, "updated": 0, "skipped": 0, "failed": 0,
            "_note": "SharePoint connector is not configured (missing credentials).",
        }

    # Resolve site info: prefer env vars, fall back to linked connections
    missing_site = not settings.sharepoint_site_id and not settings.sharepoint_site_url
    use_connection = False
    conn_hostname = conn_site_path = conn_item_path = None
    if missing_site:
        tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
        conn_hostname, conn_site_path, conn_item_path = _resolve_sharepoint_connection(tenant_id)
        if not conn_hostname:
            return {
                "status": "skipped",
                "total_files": 0, "ingested": 0, "updated": 0, "skipped": 0, "failed": 0,
                "_note": "No SharePoint site configured. Connect a SharePoint folder via 'Connect via Link' first.",
            }
        use_connection = True

    effective_limit = limit or settings.sharepoint_sync_max_files

    # 1. Resolve IDs --------------------------------------------------------
    try:
        if use_connection:
            graph, site_id, drive_id = _build_graph_for_connection(
                conn_hostname, conn_site_path
            )
            effective_path = folder_path or conn_item_path or "General"
        else:
            graph = _get_graph()
            site_id, drive_id = graph.get_site_and_drive()
            effective_path = folder_path or settings.sharepoint_folder_path
    except (GraphAuthError, GraphAPIError) as exc:
        logger.error("SharePoint auth / resolve failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "▶ SharePoint sync started – folder=%s, limit=%d, force=%s, full_scan=%s",
        effective_path, effective_limit, force, full_scan,
    )

    # Firestore service for idempotency + cursors
    firestore_svc = FirestoreService(tenant_id=DEFAULT_TENANT_ID)

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
            delta_link = _load_cursor(firestore_svc, ck)
            items, new_delta_link = graph.delta_query(
                drive_id, effective_path,
                delta_link=delta_link,
                max_items=effective_limit,
            )
            used_delta = delta_link is not None
    except (GraphAuthError, GraphAPIError) as exc:
        logger.error("SharePoint query failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    pdfs = [i for i in items if _is_supported(i)]

    # Safety guard
    if len(pdfs) > settings.sharepoint_sync_max_files:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Found {len(pdfs)} files which exceeds the safety limit of "
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
            # 3. Idempotency check via Firestore ----------------------------
            existing = firestore_svc.get_document_by_source(
                source_type="sharepoint",
                source_key="_sp_item_id",
                source_value=item_id,
            )

            if existing and not force:
                stored_etag = existing.get("stats", {}).get("_sp_etag")
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
            tmp_path = graph.download_file(drive_id, item_id, filename=item_name)

            # 5-11. Centralized pipeline ------------------------------------
            result = process_document(
                file_path=tmp_path,
                filename=item_name,
                db=db,
                tenant_id=DEFAULT_TENANT_ID,
                s3_service=_get_s3(),
                s3_url=web_url,
                file_size_bytes=item_size,
                source="sharepoint",
                source_metadata={
                    "_sp_item_id": item_id,
                    "_sp_drive_id": drive_id,
                    "_sp_web_url": web_url,
                    "source_key": src_key,
                },
                extra_metrics={
                    "_sp_etag": item_etag,
                    "_sp_item_id": item_id,
                    "_sp_drive_id": drive_id,
                    "_sp_web_url": web_url,
                },
                existing_doc_id=existing["id"] if existing else None,
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
            _save_cursor(firestore_svc, ck, new_delta_link)
            logger.info("Delta cursor saved for %s", ck)
        except Exception as exc:
            logger.warning("Failed to save delta cursor: %s", exc)

    summary = {
        "status": "completed",
        "folder_path": effective_path,
        "drive_id": drive_id,
        "total_files": len(pdfs),
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

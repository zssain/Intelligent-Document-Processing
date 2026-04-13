"""Background ingestion job manager with semaphore-based concurrency control.

Provides fire-and-forget multi-file processing with Firestore-based status
tracking and per-file progress updates.

Concurrency model
-----------------
* **Global per-instance cap** — ``MAX_CONCURRENT_INGEST`` (default 5).
  Limits total parallel file extractions across all tenants on this process.
* **Per-tenant cap** — ``MAX_CONCURRENT_INGEST_PER_TENANT`` (default 3).
  Prevents one tenant from starving others.

Both are enforced via ``asyncio.Semaphore`` and configurable through env vars.
When you migrate to Celery/ARQ, replace the semaphore dispatch with
task-queue enqueue — the Firestore job record schema is designed to be
queue-agnostic.

Firestore schema::

    tenants/{tid}/ingestion_jobs/{job_id}:
      status: queued | running | completed | failed
      source_type: s3 | sharepoint | gdrive
      created_by: str (uid)
      created_at: datetime
      queued_at: datetime
      started_at: datetime | null
      completed_at: datetime | null
      worker_id: str           # hostname:pid for future multi-worker
      files: [
        { id, name, status: pending|processing|completed|failed, error? }
      ]
      summary: { total, completed, failed }
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config.settings import settings, DEFAULT_TENANT_ID
from src.database.base import SessionLocal
from src.database.firestore_service import FirestoreService
from src.processing import process_document
from src.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

# ── Concurrency primitives (per-instance, in-process) ─────────────────────
_global_semaphore: Optional[asyncio.Semaphore] = None
_tenant_semaphores: Dict[str, asyncio.Semaphore] = {}


def _get_global_sem() -> asyncio.Semaphore:
    global _global_semaphore
    if _global_semaphore is None:
        _global_semaphore = asyncio.Semaphore(settings.max_concurrent_ingest)
    return _global_semaphore


def _get_tenant_sem(tenant_id: str) -> asyncio.Semaphore:
    if tenant_id not in _tenant_semaphores:
        _tenant_semaphores[tenant_id] = asyncio.Semaphore(
            settings.max_concurrent_ingest_per_tenant
        )
    return _tenant_semaphores[tenant_id]


_WORKER_ID = f"{platform.node()}:{os.getpid()}"


# ── Lazy S3 singleton ─────────────────────────────────────────────────────
_s3: Optional[S3Service] = None


def _get_s3() -> Optional[S3Service]:
    global _s3
    if _s3 is None:
        try:
            _s3 = S3Service()
        except Exception:
            pass
    return _s3


# ═══════════════════════════════════════════════════════════════════════════
# Job CRUD
# ═══════════════════════════════════════════════════════════════════════════

def _job_ref(tenant_id: str, job_id: str):
    from src.utils.firebase import firestore_client
    return (
        firestore_client
        .collection("tenants")
        .document(tenant_id)
        .collection("ingestion_jobs")
        .document(job_id)
    )


def create_job(
    tenant_id: str,
    user_id: str,
    source_type: str,
    files: List[Dict[str, Any]],
) -> str:
    """Create a new ingestion job document in Firestore and return job_id."""
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    file_records = [
        {"id": f["id"], "name": f["name"], "status": "pending", "error": None}
        for f in files
    ]

    job_doc = {
        "status": "queued",
        "source_type": source_type,
        "created_by": user_id,
        "created_at": now,
        "queued_at": now,
        "started_at": None,
        "completed_at": None,
        "worker_id": _WORKER_ID,
        "files": file_records,
        "summary": {"total": len(file_records), "completed": 0, "failed": 0},
    }

    _job_ref(tenant_id, job_id).set(job_doc)
    logger.info("[job] Created job %s with %d files (tenant=%s)", job_id, len(files), tenant_id)
    return job_id


def get_job(tenant_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Read a job document from Firestore."""
    doc = _job_ref(tenant_id, job_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["job_id"] = doc.id
        return data
    return None


def _update_job(tenant_id: str, job_id: str, updates: Dict[str, Any]) -> None:
    _job_ref(tenant_id, job_id).update(updates)


def _update_file_status(
    tenant_id: str,
    job_id: str,
    file_index: int,
    status: str,
    error: Optional[str] = None,
) -> None:
    """Update a single file's status inside the job's files array."""
    doc = _job_ref(tenant_id, job_id).get()
    if not doc.exists:
        return
    data = doc.to_dict()
    files = data.get("files", [])
    if file_index < len(files):
        files[file_index]["status"] = status
        if error:
            files[file_index]["error"] = error
    _job_ref(tenant_id, job_id).update({"files": files})


# ═══════════════════════════════════════════════════════════════════════════
# File downloaders (per source type)
# ═══════════════════════════════════════════════════════════════════════════

def _download_s3_file(file_id: str) -> str:
    """Download an S3 object by key and return the temp file path."""
    s3 = _get_s3()
    if not s3:
        raise RuntimeError("S3 service not available")
    return s3.download_to_tempfile(file_id)


def _download_sharepoint_file(file_id: str, filename: str = "", tenant_id: str = DEFAULT_TENANT_ID) -> str:
    """Download a SharePoint item by item_id.

    Resolves the drive from:
      1. A linked source_connection in Firestore (via Connect via Link)
      2. Falling back to env-var SHAREPOINT_SITE_ID / SHAREPOINT_SITE_URL
    """
    from src.connectors.sharepoint_graph import GraphClient

    graph = GraphClient()

    # Try linked connection first (same logic as datalake_sharepoint sync)
    drive_id = None
    if not settings.sharepoint_site_id and not settings.sharepoint_site_url:
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
                if d.get("status") == "connected" and d.get("site_hostname") and d.get("site_path"):
                    site_url = f"{d['site_hostname']}:{d['site_path']}"
                    site_id = graph.resolve_site_id(site_url)
                    drive_id = graph.resolve_drive_id(site_id)
                    logger.info("[job] Resolved SharePoint drive from linked connection: %s", drive_id)
                    break
        except Exception as exc:
            logger.warning("[job] Could not resolve SharePoint from linked connections: %s", exc)

    if not drive_id:
        _site_id, drive_id = graph.get_site_and_drive()

    return graph.download_file(drive_id, file_id, filename=filename)


def _download_gdrive_file(file_id: str, filename: str = "") -> str:
    """Download a Google Drive file by file_id."""
    from src.connectors.google_drive import GoogleDriveClient
    gdrive = GoogleDriveClient()
    return gdrive.download_file(file_id, filename=filename)


_DOWNLOADERS = {
    "s3": lambda f, tid=DEFAULT_TENANT_ID: _download_s3_file(f["id"]),
    "sharepoint": lambda f, tid=DEFAULT_TENANT_ID: _download_sharepoint_file(f["id"], f.get("name", ""), tenant_id=tid),
    "gdrive": lambda f, tid=DEFAULT_TENANT_ID: _download_gdrive_file(f["id"], f.get("name", "")),
}


# ═══════════════════════════════════════════════════════════════════════════
# Job runner
# ═══════════════════════════════════════════════════════════════════════════

async def run_job(tenant_id: str, job_id: str) -> None:
    """Execute all files in a job with semaphore-based concurrency.

    This function is designed to be dispatched via ``BackgroundTasks``.
    It runs each file sequentially (acquiring both the global and per-tenant
    semaphores before processing) and updates Firestore after each file.
    """
    _update_job(tenant_id, job_id, {
        "status": "running",
        "started_at": datetime.now(timezone.utc),
        "worker_id": _WORKER_ID,
    })

    job = get_job(tenant_id, job_id)
    if not job:
        logger.error("[job] Job %s not found", job_id)
        return

    source_type = job["source_type"]
    files = job["files"]
    downloader = _DOWNLOADERS.get(source_type)

    if not downloader:
        logger.error("[job] Unknown source_type '%s' for job %s", source_type, job_id)
        _update_job(tenant_id, job_id, {
            "status": "failed",
            "completed_at": datetime.now(timezone.utc),
        })
        return

    s3_service = _get_s3()
    completed = 0
    failed = 0
    global_sem = _get_global_sem()
    tenant_sem = _get_tenant_sem(tenant_id)

    for idx, file_rec in enumerate(files):
        # Acquire both semaphores
        async with global_sem:
            async with tenant_sem:
                tmp_path: Optional[str] = None
                try:
                    _update_file_status(tenant_id, job_id, idx, "processing")

                    # Download
                    tmp_path = await asyncio.to_thread(downloader, file_rec, tenant_id)

                    # Build source metadata
                    source_metadata = {"source_key": file_rec["id"]}
                    extra_metrics: Dict[str, Any] = {}
                    if source_type == "s3":
                        source_metadata["s3_key"] = file_rec["id"]
                    elif source_type == "sharepoint":
                        source_metadata["_sp_item_id"] = file_rec["id"]
                    elif source_type == "gdrive":
                        source_metadata["_gdrive_file_id"] = file_rec["id"]

                    # Process (synchronous — runs in thread via to_thread)
                    db: Session = SessionLocal()
                    try:
                        result = await asyncio.to_thread(
                            process_document,
                            file_path=tmp_path,
                            filename=file_rec["name"],
                            db=db,
                            tenant_id=tenant_id,
                            s3_service=s3_service,
                            source=source_type,
                            source_metadata=source_metadata,
                            extra_metrics=extra_metrics,
                            created_by_uid=job.get("created_by", ""),
                        )
                        db.commit()
                        completed += 1
                        _update_file_status(tenant_id, job_id, idx, "completed")
                        logger.info(
                            "[job] File %s completed (doc=%s, chunks=%d)",
                            file_rec["name"],
                            result.document_id,
                            result.chunks_count,
                        )
                    except Exception as exc:
                        db.rollback()
                        raise exc
                    finally:
                        db.close()

                except Exception as exc:
                    failed += 1
                    err_msg = f"{type(exc).__name__}: {exc}"
                    _update_file_status(tenant_id, job_id, idx, "failed", error=err_msg)
                    logger.error(
                        "[job] File %s failed: %s", file_rec["name"], err_msg, exc_info=True
                    )
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass

    # Final status
    final_status = "completed" if failed == 0 else ("failed" if completed == 0 else "completed")
    _update_job(tenant_id, job_id, {
        "status": final_status,
        "completed_at": datetime.now(timezone.utc),
        "summary": {"total": len(files), "completed": completed, "failed": failed},
    })

    logger.info(
        "[job] Job %s finished: %d completed, %d failed out of %d",
        job_id, completed, failed, len(files),
    )

"""Datalake S3 endpoints – list & incremental sync.

These endpoints allow the backend to discover PDFs in the S3 datalake bucket
and ingest them through the same Azure CU → normalize → chunk → embed → pgvector
pipeline used by ``/api/v1/rag/ingest``.

Idempotency
-----------
Each S3 object is tracked via a *source_key* stored in ``Document.source``
(``s3:<bucket>:<key>``).  The ETag is stored separately in the document's
``metrics`` JSON under ``_s3_etag``.  When the same key appears again with a
*different* ETag (i.e. the file was replaced in S3) the old chunks are deleted
and the Document row is updated in-place.

Safety
------
* ``s3_sync_max_files`` (default 500) prevents accidentally ingesting 50k PDFs.
* Each file is processed in isolation – one bad PDF does not stop the sync.
* Per-file DB rollback on failure.
* Retry with exponential back-off for CU & embedding calls (3 attempts).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session

from config.settings import settings
from src.database.base import get_db
from src.database.models import Document
from src.processing import process_document
from src.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_s3_service: Optional[S3Service] = None


def _get_s3() -> S3Service:
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service


# ---------------------------------------------------------------------------
# Simple API-key auth guard (same key for all protected endpoints)
# ---------------------------------------------------------------------------
def _verify_api_key(x_api_key: str = Header(default="")) -> None:
    """Require X-API-Key header when ``settings.api_key`` is set.

    When ``settings.api_key`` is empty (dev default) **all** requests are
    allowed so local development is frictionless.
    """
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _source_key(bucket: str, key: str) -> str:
    """Build the deterministic source identifier stored in ``Document.source``."""
    return f"s3:{bucket}:{key}"


def _s3_url(bucket: str, region: str, key: str) -> str:
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


# ---------------------------------------------------------------------------
# GET /s3/list
# ---------------------------------------------------------------------------
@router.get("/s3/list", dependencies=[Depends(_verify_api_key)])
async def list_datalake_pdfs(
    prefix: str = Query(default=None, description="S3 prefix to list (default: settings.s3_datalake_prefix)"),
    limit: int = Query(default=100, ge=1, le=5000, description="Max items to return"),
):
    """List PDF objects in the datalake S3 prefix."""
    effective_prefix = prefix or settings.s3_datalake_prefix
    try:
        s3 = _get_s3()
        objects = s3.list_objects(prefix=effective_prefix, max_keys=limit)
    except Exception as exc:
        logger.error("S3 list failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"S3 list failed: {exc}") from exc

    # Filter PDFs only
    pdfs = [o for o in objects if o["key"].lower().endswith(".pdf")]

    return {
        "prefix": effective_prefix,
        "total_objects": len(objects),
        "total_pdfs": len(pdfs),
        "pdfs": pdfs,
    }


# ---------------------------------------------------------------------------
# POST /s3/sync
# ---------------------------------------------------------------------------
@router.post("/s3/sync", dependencies=[Depends(_verify_api_key)])
async def sync_datalake(
    prefix: str = Query(default=None, description="S3 prefix to sync"),
    limit: int = Query(default=None, ge=1, description="Max PDFs to process"),
    force: bool = Query(default=False, description="Re-process even if already ingested"),
    db: Session = Depends(get_db),
):
    """Incrementally ingest PDFs from the S3 datalake into the RAG pipeline.

    Each PDF is identified by its S3 key.  The ETag is used as a version
    marker – when it changes the document is re-processed in-place.
    """
    effective_prefix = prefix or settings.s3_datalake_prefix
    effective_limit = limit or settings.s3_sync_max_files

    logger.info("▶ datalake sync started – prefix=%s, limit=%d, force=%s",
                effective_prefix, effective_limit, force)

    # 1. List objects -------------------------------------------------------
    try:
        s3 = _get_s3()
        all_objects = s3.list_objects(prefix=effective_prefix, max_keys=effective_limit)
    except Exception as exc:
        logger.error("S3 list failed during sync: %s", exc)
        raise HTTPException(status_code=502, detail=f"S3 list failed: {exc}") from exc

    pdfs = [o for o in all_objects if o["key"].lower().endswith(".pdf")]

    # Safety guard
    if len(pdfs) > settings.s3_sync_max_files:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Found {len(pdfs)} PDFs which exceeds the safety limit of "
                f"{settings.s3_sync_max_files}. Narrow the prefix or raise "
                "S3_SYNC_MAX_FILES."
            ),
        )

    ingested = 0
    skipped = 0
    updated = 0
    failed = 0
    errors: list[dict] = []

    for obj in pdfs:
        key: str = obj["key"]
        etag: str = obj["etag"]
        file_size: int = obj["size"]
        src_key = _source_key(s3.bucket_name, key)

        tmp_path: Optional[str] = None
        try:
            # 2. Idempotency check ------------------------------------------
            existing: Optional[Document] = (
                db.query(Document).filter(Document.source == src_key).first()
            )

            if existing and not force:
                stored_etag = (existing.metrics or {}).get("_s3_etag")
                if stored_etag == etag:
                    logger.debug("SKIP (unchanged) %s", key)
                    skipped += 1
                    continue
                logger.info("ETag changed for %s (old=%s new=%s) – re-processing",
                            key, stored_etag, etag)

            if existing and force:
                stored_etag = (existing.metrics or {}).get("_s3_etag")
                if stored_etag == etag and force:
                    logger.info("FORCE re-process %s", key)

            # 3. Download ---------------------------------------------------
            tmp_path = s3.download_to_tempfile(key)

            # 4–10. Centralized pipeline ------------------------------------
            result = process_document(
                file_path=tmp_path,
                filename=os.path.basename(key),
                db=db,
                s3_service=s3,
                s3_url=_s3_url(s3.bucket_name, settings.aws_region, key),
                file_size_bytes=file_size,
                source=src_key,
                extra_metrics={"_s3_etag": etag, "_s3_key": key},
                existing_doc=existing,
            )

            db.commit()

            if existing:
                updated += 1
                logger.info("UPDATED document %s for key %s", result.document_id, key)
            else:
                ingested += 1
                logger.info("INGESTED document %s for key %s", result.document_id, key)

        except Exception as exc:
            db.rollback()
            failed += 1
            err_msg = f"{type(exc).__name__}: {exc}"
            errors.append({"key": key, "error": err_msg})
            logger.error("FAILED to process %s: %s", key, err_msg, exc_info=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    summary = {
        "status": "completed",
        "prefix": effective_prefix,
        "total_pdfs": len(pdfs),
        "ingested": ingested,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }
    if errors:
        summary["errors"] = errors

    logger.info("▶ datalake sync finished – %s", summary)
    return summary

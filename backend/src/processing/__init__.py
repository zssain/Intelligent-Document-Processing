"""Centralized document processing pipeline.

This module provides a single ``process_document`` function that orchestrates
the full ingestion flow:

    PDF → Azure CU → Normalize → Chunk → Embed → Store (DB + pgvector)

Both the ``/rag/ingest`` endpoint and the datalake sync jobs delegate to this
module so the business logic is never duplicated.
"""

from __future__ import annotations

import logging
import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from src.cu.client import ContentUnderstandingService
from src.cu.normalizer import DocumentNormalizer
from src.rag.chunker import Chunker
from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore
from src.database.models import Document, DocumentChunk
from src.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singletons – heavy clients are only created once.
# ---------------------------------------------------------------------------
_cu: Optional[ContentUnderstandingService] = None
_normalizer = DocumentNormalizer()
_chunker = Chunker()
_embedder: Optional[Embedder] = None


def _get_cu() -> ContentUnderstandingService:
    global _cu
    if _cu is None:
        _cu = ContentUnderstandingService()
    return _cu


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


class IngestionResult:
    """Holds the result of a single document ingestion."""

    def __init__(
        self,
        document_id: str,
        filename: str,
        chunks_count: int,
        entity: str = "",
        document_type: str = "",
        s3_url: Optional[str] = None,
    ):
        self.document_id = document_id
        self.filename = filename
        self.chunks_count = chunks_count
        self.entity = entity
        self.document_type = document_type
        self.s3_url = s3_url


def process_document(
    file_path: str,
    filename: str,
    db: Session,
    *,
    s3_service: Optional[S3Service] = None,
    s3_url: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    source: str = "local",
    extra_metrics: Optional[Dict[str, Any]] = None,
    existing_doc: Optional[Document] = None,
) -> IngestionResult:
    """Run the full ingestion pipeline for one document.

    The entire operation runs inside the caller's DB session.  The caller is
    responsible for ``db.commit()`` on success and ``db.rollback()`` on
    failure so that either *everything* is persisted or *nothing* is.

    Parameters
    ----------
    file_path:
        Absolute path to the local PDF file.
    filename:
        Original filename (used for display / S3 keys).
    db:
        Active SQLAlchemy session – **not** committed here.
    s3_service:
        Optional S3 helper.  When provided, raw & normalized JSON artefacts
        are uploaded to S3.
    s3_url:
        Pre-existing S3 URL for the source PDF (e.g. already uploaded).
    file_size_bytes:
        Size of the source PDF in bytes.
    source:
        Source identifier string (``"local"``, ``"s3:<bucket>:<key>"``, etc.).
    extra_metrics:
        Additional keys to merge into the ``metrics`` JSON column
        (e.g. ``{"_s3_etag": "abc123"}``).
    existing_doc:
        When updating an already-ingested document pass the existing
        ``Document`` row.  Old chunks are deleted and fields are updated
        in-place instead of inserting a new row.

    Returns
    -------
    IngestionResult
    """

    if file_size_bytes is None and os.path.exists(file_path):
        file_size_bytes = os.path.getsize(file_path)

    # ── 1. Azure Content Understanding ────────────────────────────────
    logger.info("[pipeline] Analyzing %s with Azure CU…", filename)
    raw_cu_data = _get_cu().analyze_document(file_path)

    # ── 2. Normalize ──────────────────────────────────────────────────
    logger.info("[pipeline] Normalizing CU output…")
    normalized_data = _normalizer.normalize(raw_cu_data)

    # ── 3. Upload artefacts to S3 (optional) ──────────────────────────
    raw_s3_url: Optional[str] = None
    normalized_s3_url: Optional[str] = None

    if s3_service:
        try:
            unique_pfx = uuid.uuid4().hex[:8]
            base = os.path.splitext(filename)[0]

            raw_s3_url = s3_service.upload_json(
                json.dumps(raw_cu_data, default=str),
                f"{unique_pfx}_{base}_raw.json",
                "processed/raw/",
            )
            normalized_s3_url = s3_service.upload_json(
                json.dumps(normalized_data, default=str),
                f"{unique_pfx}_{base}_normalized.json",
                "processed/normalized/",
            )
            logger.info("[pipeline] Artefacts uploaded to S3")
        except Exception as exc:
            logger.warning("[pipeline] S3 artefact upload failed (non-fatal): %s", exc)

    # ── 4. Chunk ──────────────────────────────────────────────────────
    logger.info("[pipeline] Chunking document…")
    markdown_text = raw_cu_data.get("markdown", "")
    chunks = _chunker.chunk_document(normalized_data, markdown_text)

    if not chunks:
        logger.warning("[pipeline] Chunker produced 0 chunks for %s", filename)

    # ── 5. Embed ──────────────────────────────────────────────────────
    logger.info("[pipeline] Generating embeddings for %d chunks…", len(chunks))
    embedder = _get_embedder()
    if chunks:
        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed_batch(texts)
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i]

    # ── 5b. Upload chunks + embeddings to S3 processed folder ─────────
    if s3_service and chunks:
        try:
            unique_pfx = uuid.uuid4().hex[:8]
            base = os.path.splitext(filename)[0]
            # Strip the raw embedding vectors for the JSON artifact (too large)
            # but keep text, chunk_type, and metadata for auditability
            chunks_for_s3 = [
                {
                    "text": c["text"],
                    "chunk_type": c["chunk_type"],
                    "metadata": c.get("metadata", {}),
                    "embedding_dim": len(c["embedding"]) if "embedding" in c else 0,
                }
                for c in chunks
            ]
            s3_service.upload_json(
                json.dumps(chunks_for_s3, default=str),
                f"{unique_pfx}_{base}_chunks.json",
                "processed/chunks/",
            )
            logger.info("[pipeline] Chunks artefact uploaded to S3 (%d chunks)", len(chunks))
        except Exception as exc:
            logger.warning("[pipeline] S3 chunks upload failed (non-fatal): %s", exc)

    # ── 6. Persist Document row ───────────────────────────────────────
    metrics = normalized_data.get("metrics") or {}
    if extra_metrics:
        metrics.update(extra_metrics)

    if existing_doc:
        # UPDATE path – wipe old chunks, update fields
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == existing_doc.id
        ).delete(synchronize_session=False)

        existing_doc.filename = filename
        existing_doc.document_type = normalized_data.get("document_type", existing_doc.document_type)
        existing_doc.entity = normalized_data.get("entity", existing_doc.entity)
        existing_doc.period_end = normalized_data.get("period_end", existing_doc.period_end)
        existing_doc.metrics = metrics
        existing_doc.confidence = normalized_data.get("source", {}).get("confidence", 0.95)
        existing_doc.raw_cu_output_path = raw_s3_url or existing_doc.raw_cu_output_path
        existing_doc.normalized_output_path = normalized_s3_url or existing_doc.normalized_output_path
        existing_doc.s3_url = s3_url or existing_doc.s3_url
        existing_doc.file_size_bytes = file_size_bytes or existing_doc.file_size_bytes
        existing_doc.processed_at = datetime.utcnow()

        db.flush()
        doc_record = existing_doc
        logger.info("[pipeline] Updated Document %s", doc_record.id)
    else:
        doc_record = Document(
            filename=filename,
            document_type=normalized_data.get("document_type", "Document"),
            entity=normalized_data.get("entity", "Unknown Entity"),
            period_end=normalized_data.get("period_end"),
            metrics=metrics,
            source=source,
            confidence=normalized_data.get("source", {}).get("confidence", 0.95),
            raw_cu_output_path=raw_s3_url,
            normalized_output_path=normalized_s3_url,
            s3_url=s3_url,
            file_size_bytes=file_size_bytes,
        )
        db.add(doc_record)
        db.flush()   # assigns doc_record.id without committing
        logger.info("[pipeline] Inserted Document %s", doc_record.id)

    # ── 7. Store chunks in pgvector ───────────────────────────────────
    if chunks:
        vector_store = VectorStore(db)
        vector_store.add_chunks(doc_record.id, chunks)
        logger.info("[pipeline] Stored %d chunks for document %s", len(chunks), doc_record.id)

    return IngestionResult(
        document_id=str(doc_record.id),
        filename=filename,
        chunks_count=len(chunks),
        entity=normalized_data.get("entity", ""),
        document_type=normalized_data.get("document_type", ""),
        s3_url=s3_url,
    )

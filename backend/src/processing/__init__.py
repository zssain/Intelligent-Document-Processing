"""Centralized document processing pipeline.

This module provides a single ``process_document`` function that orchestrates
the full ingestion flow:

    PDF → Docling+Gemini (or Azure DI fallback) → Normalize → Chunk → Embed → Store (Firestore + pgvector)

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
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from src.storage.s3_service import S3Service
from config.settings import DEFAULT_TENANT_ID

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
    tenant_id: str = DEFAULT_TENANT_ID,
    classification_level: int = 1,
    category_ids: Optional[list[str]] = None,
    s3_service: Optional[S3Service] = None,
    s3_url: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    source: str = "local",
    source_metadata: Optional[Dict[str, Any]] = None,
    extra_metrics: Optional[Dict[str, Any]] = None,
    existing_doc_id: Optional[str] = None,
    created_by_uid: str = "",
) -> IngestionResult:
    """Run the full ingestion pipeline for one document.

    The entire operation runs inside the caller's DB session for Postgres chunks.
    Firestore document metadata is written separately. The caller is responsible
    for ``db.commit()`` on success and ``db.rollback()`` on failure.

    Parameters
    ----------
    file_path:
        Absolute path to the local PDF file.
    filename:
        Original filename (used for display / S3 keys).
    db:
        Active SQLAlchemy session for Postgres – **not** committed here.
    tenant_id:
        Tenant ID for multi-tenancy.
    classification_level:
        Security clearance level (0-3).
    category_ids:
        List of category IDs for access control.
    s3_service:
        Optional S3 helper for uploading artifacts.
    s3_url:
        Pre-existing S3 URL for the source PDF.
    file_size_bytes:
        Size of the source PDF in bytes.
    source:
        Source identifier string (``"local"``, ``"s3"``, ``"sharepoint"``, etc.).
    source_metadata:
        Source-specific metadata (e.g., s3_key, etag, drive_id, etc.).
    extra_metrics:
        Additional metrics to store in Firestore document.
    existing_doc_id:
        When updating an already-ingested document, pass the Firestore doc ID.
        Old chunks are deleted and the document is updated.
    created_by_uid:
        UID of user who initiated this ingestion.

    Returns
    -------
    IngestionResult
    """

    if file_size_bytes is None and os.path.exists(file_path):
        file_size_bytes = os.path.getsize(file_path)
    
    category_ids = category_ids or []
    source_metadata = source_metadata or {}

    # ── 1. Document Extraction (Docling+Gemini / Azure DI) ──────────────
    logger.info("[pipeline] Analyzing %s with extraction backend…", filename)
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

            # Store raw DI markdown for future GPT-4o re-processing
            raw_extraction_url = s3_service.upload_json(
                json.dumps({"markdown": raw_cu_data.get("markdown", ""), "fields": raw_cu_data.get("fields", {})}, default=str),
                f"{unique_pfx}_{base}_raw_extraction.json",
                "processed/raw_extraction/",
            )

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

    # ── 6. Persist Document metadata to Firestore ─────────────────────
    entity_name = normalized_data.get("entity", "Unknown Entity")
    document_type = normalized_data.get("document_type", "Document")
    document_language = normalized_data.get("document_language", "en")
    doc_title = normalized_data.get("title") or filename
    doc_summary = normalized_data.get("summary", "")
    period = normalized_data.get("period_end", "")
    confidence = normalized_data.get("source", {}).get("confidence", 0.0)
    extraction_variant = raw_cu_data.get("metadata", {}).get("extraction_variant", "docling_gemini")
    
    metrics = normalized_data.get("metrics") or {}
    if extra_metrics:
        metrics.update(extra_metrics)
    
    # Generate or use existing document ID
    doc_id = existing_doc_id or uuid.uuid4().hex
    now = datetime.utcnow()
    
    firestore_svc = FirestoreService(tenant_id=tenant_id)
    
    stats_data = {
        "chunks_count": len(chunks),
        "file_size_bytes": file_size_bytes or 0,
        **metrics,
    }
    
    if existing_doc_id:
        # UPDATE path – delete old chunks, update Firestore doc
        logger.info("[pipeline] Updating existing document %s", doc_id)
        
        # Delete old chunks from Postgres
        db.query(DocumentChunk).filter(
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.doc_id == doc_id
        ).delete(synchronize_session=False)
        
        # Update Firestore document
        firestore_svc.update_document(doc_id, {
            "title": doc_title,
            "entity_name": entity_name,
            "document_type": document_type,
            "document_language": document_language,
            "summary": doc_summary,
            "period": period,
            "confidence": confidence,
            "s3_url": s3_url or "",
            "normalized_url": normalized_s3_url or "",
            "classification_level": classification_level,
            "category_ids": category_ids,
            "source_metadata": source_metadata,
            "extraction_variant": extraction_variant,
            "enhancement_status": "none",
            "stats": stats_data,
        })
    else:
        # CREATE path – new document in Firestore
        logger.info("[pipeline] Creating new document %s", doc_id)
        firestore_svc.create_document(
            doc_id=doc_id,
            title=doc_title,
            source_type=source,
            source_metadata=source_metadata,
            classification_level=classification_level,
            category_ids=category_ids,
            entity_name=entity_name,
            document_type=document_type,
            document_language=document_language,
            summary=doc_summary,
            period=period,
            s3_url=s3_url or "",
            normalized_url=normalized_s3_url or "",
            confidence=confidence,
            created_by_uid=created_by_uid,
            status="active",
            extraction_variant=extraction_variant,
            enhancement_status="none",
            stats=stats_data,
        )

    # ── 7. Store chunks in Postgres with denormalized metadata ────────
    if chunks:
        # Denormalize entity_name and document_type into each chunk's metadata
        for chunk in chunks:
            chunk_meta = chunk.get("metadata", {})
            chunk_meta["entity_name"] = entity_name
            chunk_meta["document_type"] = document_type
            chunk_meta["period"] = period
            chunk["metadata"] = chunk_meta
        
        vector_store = VectorStore(db)
        vector_store.add_chunks(
            doc_id=doc_id,
            tenant_id=tenant_id,
            classification_level=classification_level,
            category_ids=category_ids,
            chunks=chunks
        )
        logger.info("[pipeline] Stored %d chunks for document %s", len(chunks), doc_id)

    return IngestionResult(
        document_id=doc_id,
        filename=filename,
        chunks_count=len(chunks),
        entity=entity_name,
        document_type=document_type,
        s3_url=s3_url,
    )

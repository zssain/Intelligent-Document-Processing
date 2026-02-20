"""Sync document classification / category policy from Firestore → Postgres.

When an admin changes a document's ``classification_level`` or
``category_ids`` in Firestore, the denormalized copies stored on every
matching ``document_chunks`` row in Postgres must be updated to keep
RBAC filtering consistent.

Usage
-----
::

    from src.utils.sync_policy import sync_doc_policy

    # After updating the document in Firestore:
    updated = sync_doc_policy(doc_id="abc123", tenant_id="default-tenant", db=db)
    db.commit()
    print(f"Updated {updated} chunk rows")

The function is intentionally **synchronous** so it can participate in an
existing SQLAlchemy transaction managed by the caller.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.database.firestore_service import FirestoreService
from src.database.models import DocumentChunk

logger = logging.getLogger(__name__)


def sync_doc_policy(
    doc_id: str,
    tenant_id: str,
    db: Session,
    *,
    classification_level: Optional[int] = None,
    category_ids: Optional[list[str]] = None,
    auto_commit: bool = False,
) -> int:
    """Read current policy from Firestore and batch-update Postgres chunks.

    Parameters
    ----------
    doc_id:
        The Firestore document ID whose policy changed.
    tenant_id:
        Tenant owning the document.
    db:
        An active SQLAlchemy session.  The caller is responsible for
        committing unless ``auto_commit=True``.
    classification_level:
        If provided, use this value instead of reading from Firestore.
        Useful when the caller already has the new value in hand.
    category_ids:
        If provided, use this value instead of reading from Firestore.
    auto_commit:
        When ``True``, the function commits the transaction itself.
        Default is ``False`` so the caller can batch multiple syncs
        in a single commit.

    Returns
    -------
    int
        Number of ``document_chunks`` rows updated.

    Raises
    ------
    ValueError
        If the document does not exist in Firestore and no explicit
        values were supplied.
    """

    # ------------------------------------------------------------------
    # 1. Resolve policy values
    # ------------------------------------------------------------------
    if classification_level is None or category_ids is None:
        fs = FirestoreService(tenant_id=tenant_id)
        doc_data = fs.get_document(doc_id)

        if doc_data is None:
            raise ValueError(
                f"Document {doc_id} not found in Firestore tenant {tenant_id}"
            )

        if classification_level is None:
            classification_level = doc_data.get("classification_level", 1)
        if category_ids is None:
            category_ids = doc_data.get("category_ids", [])

    logger.info(
        "Syncing policy for doc %s → classification_level=%d, category_ids=%s",
        doc_id,
        classification_level,
        category_ids,
    )

    # ------------------------------------------------------------------
    # 2. Batch-update matching chunks in Postgres
    # ------------------------------------------------------------------
    rows_updated: int = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.doc_id == doc_id,
            DocumentChunk.tenant_id == tenant_id,
        )
        .update(
            {
                DocumentChunk.classification_level: classification_level,
                DocumentChunk.category_ids: category_ids,
            },
            synchronize_session="fetch",
        )
    )

    if auto_commit:
        db.commit()

    logger.info(
        "Policy sync complete for doc %s: %d chunk rows updated",
        doc_id,
        rows_updated,
    )
    return rows_updated


def sync_bulk_doc_policy(
    doc_ids: list[str],
    tenant_id: str,
    db: Session,
    *,
    auto_commit: bool = False,
) -> dict[str, int]:
    """Sync policy for multiple documents in one transaction.

    Reads each document's current policy from Firestore and batch-updates
    the corresponding ``document_chunks`` rows.

    Parameters
    ----------
    doc_ids:
        List of Firestore document IDs to sync.
    tenant_id:
        Tenant owning the documents.
    db:
        Active SQLAlchemy session.
    auto_commit:
        Commit the transaction after all updates.

    Returns
    -------
    dict[str, int]
        Mapping of ``doc_id → rows_updated``.
    """

    results: dict[str, int] = {}

    for doc_id in doc_ids:
        try:
            updated = sync_doc_policy(doc_id, tenant_id, db)
            results[doc_id] = updated
        except ValueError as exc:
            logger.warning("Skipping %s: %s", doc_id, exc)
            results[doc_id] = 0
        except Exception as exc:
            logger.error(
                "Failed to sync policy for %s: %s", doc_id, exc, exc_info=True
            )
            results[doc_id] = -1

    if auto_commit:
        db.commit()

    return results

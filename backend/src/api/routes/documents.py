"""Document listing endpoint for all authenticated users.

GET /api/v1/documents – returns documents from Firestore with
role-based visibility:

* **org_admin / admin** → sees all non-deleted documents.
* **Regular users** → sees only documents where:
    - ``classification_level <= user.clearance_level``
    - ``category_ids`` overlaps with ``user.allowed_category_ids``
      (or doc has no categories — treated as public)
    - ``deleted_at == null``
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from config.settings import DEFAULT_TENANT_ID
from src.api.auth import CurrentUser, get_current_user, get_user_doc_filter
from src.database.firestore_service import FirestoreService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents", summary="List accessible documents")
async def list_documents(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    source_type: str = Query(default=None, description="Filter by source type"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List documents from Firestore respecting RBAC visibility.

    * Admin users see all non-deleted documents.
    * Regular users see only documents matching their clearance and
      allowed categories.
    """
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    fs = FirestoreService(tenant_id=tenant_id)

    # Fetch active (non-deleted) documents
    all_docs = fs.list_documents(
        status="active",
        source_type=source_type,
        limit=limit,
        offset=offset,
    )

    doc_filter = get_user_doc_filter(current_user)

    # Admin → no filtering
    if doc_filter is None:
        return {"documents": all_docs, "total": len(all_docs)}

    # Regular user → filter by clearance + categories
    user_clearance: int = doc_filter["clearance_level"]
    user_cats: List[str] = doc_filter["allowed_category_ids"]

    visible: List[Dict[str, Any]] = []
    for doc in all_docs:
        doc_level = doc.get("classification_level", 0)
        doc_cats = doc.get("category_ids", [])

        # Clearance check
        if doc_level > user_clearance:
            continue

        # Category overlap check (empty category_ids → public document)
        if doc_cats and user_cats:
            if not set(doc_cats).intersection(user_cats):
                continue
        elif doc_cats and not user_cats:
            # Doc has categories but user has none → denied
            continue

        visible.append(doc)

    return {"documents": visible, "total": len(visible)}

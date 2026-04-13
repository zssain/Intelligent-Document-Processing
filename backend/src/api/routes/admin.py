"""Admin management API routes.

All endpoints in this module require the ``org_admin`` role.  They are
mounted under ``/admin`` by ``main.py`` and protected by both the global
``get_current_user`` dependency *and* a router-level
``require_role("org_admin")`` guard.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from firebase_admin import auth as firebase_auth

from config.settings import DEFAULT_TENANT_ID
from src.api.auth import CurrentUser, get_current_user, require_role, SOURCES, ACTIONS
from src.database.base import get_db
from src.database.firestore_service import FirestoreService
from src.utils.sync_policy import sync_doc_policy, sync_bulk_doc_policy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router – every endpoint requires org_admin
# ---------------------------------------------------------------------------
router = APIRouter(
    dependencies=[Depends(require_role("org_admin"))],
)


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------
class UpdateRoleRequest(BaseModel):
    role: str = Field(..., description="New role (e.g. org_admin, viewer, editor)")


class UpdateClearanceRequest(BaseModel):
    clearance_level: int = Field(
        ..., ge=0, le=10, description="New clearance level"
    )


class UpdateCategoriesRequest(BaseModel):
    allowed_category_ids: List[str] = Field(
        ..., description="New list of allowed category IDs"
    )


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Category display name")
    description: str = Field("", description="Optional description")


class UpdateClassificationRequest(BaseModel):
    classification_level: int = Field(
        ..., ge=0, le=10, description="New classification level"
    )


class BulkCategorizeRequest(BaseModel):
    doc_ids: List[str] = Field(
        ..., min_length=1, description="List of document IDs"
    )
    category_ids: List[str] = Field(
        ..., description="Category IDs to assign"
    )


class SoftDeleteRequest(BaseModel):
    reason: str = Field("", description="Reason for deletion")


class SourceActionPermissions(BaseModel):
    """Permissions for a single source."""
    can_view: bool = False
    can_download: bool = False
    can_filter: bool = False
    can_sync: bool = False
    can_preview: bool = False


class UpdateSourcePermissionsRequest(BaseModel):
    """Full source_permissions map."""
    source_permissions: Dict[str, SourceActionPermissions] = Field(
        ..., description="Map of source name to action permissions"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fs(user: CurrentUser) -> FirestoreService:
    """Build a tenant-scoped Firestore service from the current user."""
    tid = user.tenant_id or DEFAULT_TENANT_ID
    return FirestoreService(tenant_id=tid)


# ===================================================================
#  USER MANAGEMENT
# ===================================================================

@router.get("/users", summary="List tenant users")
async def list_users(
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all users in the tenant from Firestore."""
    fs = _fs(current_user)
    users = fs.list_users()
    return {"users": users}


@router.post("/users/{uid}/role", summary="Update user role")
async def update_user_role(
    uid: str,
    body: UpdateRoleRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a user's role in Firestore and sync to Firebase custom claims."""
    fs = _fs(current_user)

    # Read current state for audit
    existing = fs.get_user(uid)
    if not existing:
        raise HTTPException(status_code=404, detail=f"User {uid} not found")

    old_role = existing.get("role", "")

    # 1. Update Firestore profile
    fs.update_user(uid, {"role": body.role})

    # 2. Sync Firebase Auth custom claims
    try:
        # Preserve existing custom claims, update role
        user_record = firebase_auth.get_user(uid)
        claims = dict(user_record.custom_claims or {})
        claims["role"] = body.role
        firebase_auth.set_custom_user_claims(uid, claims)
    except Exception as exc:
        logger.error("Failed to update Firebase custom claims for %s: %s", uid, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Firestore updated but Firebase Auth claims sync failed: {exc}",
        )

    # 3. Audit log
    fs.create_audit_event(
        event_type="user.role_updated",
        actor_uid=current_user.uid,
        entity_type="user",
        entity_id=uid,
        before={"role": old_role},
        after={"role": body.role},
    )

    return {"status": "ok", "uid": uid, "role": body.role}


@router.put("/users/{uid}/clearance", summary="Update user clearance level")
async def update_user_clearance(
    uid: str,
    body: UpdateClearanceRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update clearance_level in Firestore + Firebase custom claims."""
    fs = _fs(current_user)

    existing = fs.get_user(uid)
    if not existing:
        raise HTTPException(status_code=404, detail=f"User {uid} not found")

    old_clearance = existing.get("clearance_level", 0)

    # 1. Firestore
    fs.update_user(uid, {"clearance_level": body.clearance_level})

    # 2. Firebase Auth custom claims
    try:
        user_record = firebase_auth.get_user(uid)
        claims = dict(user_record.custom_claims or {})
        claims["clearance_level"] = body.clearance_level
        firebase_auth.set_custom_user_claims(uid, claims)
    except Exception as exc:
        logger.error("Failed to update claims for %s: %s", uid, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Firestore updated but Firebase Auth claims sync failed: {exc}",
        )

    # 3. Audit log
    fs.create_audit_event(
        event_type="user.clearance_updated",
        actor_uid=current_user.uid,
        entity_type="user",
        entity_id=uid,
        before={"clearance_level": old_clearance},
        after={"clearance_level": body.clearance_level},
    )

    return {
        "status": "ok",
        "uid": uid,
        "clearance_level": body.clearance_level,
    }


@router.put("/users/{uid}/categories", summary="Update user allowed categories")
async def update_user_categories(
    uid: str,
    body: UpdateCategoriesRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update allowed_category_ids in Firestore."""
    fs = _fs(current_user)

    existing = fs.get_user(uid)
    if not existing:
        raise HTTPException(status_code=404, detail=f"User {uid} not found")

    old_cats = existing.get("allowed_category_ids", [])

    fs.update_user(uid, {"allowed_category_ids": body.allowed_category_ids})

    fs.create_audit_event(
        event_type="user.categories_updated",
        actor_uid=current_user.uid,
        entity_type="user",
        entity_id=uid,
        before={"allowed_category_ids": old_cats},
        after={"allowed_category_ids": body.allowed_category_ids},
    )

    return {
        "status": "ok",
        "uid": uid,
        "allowed_category_ids": body.allowed_category_ids,
    }


@router.put("/users/{uid}/source-permissions", summary="Update user source permissions")
async def update_user_source_permissions(
    uid: str,
    body: UpdateSourcePermissionsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update per-source action permissions in Firestore."""
    fs = _fs(current_user)

    existing = fs.get_user(uid)
    if not existing:
        raise HTTPException(status_code=404, detail=f"User {uid} not found")

    old_perms = existing.get("source_permissions", {})

    # Validate source names
    new_perms = {}
    for source, actions in body.source_permissions.items():
        if source not in SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown source '{source}'. Valid: {SOURCES}",
            )
        new_perms[source] = actions.model_dump()

    # Update Firestore
    fs.update_user(uid, {"source_permissions": new_perms})

    # Audit log
    fs.create_audit_event(
        event_type="user.source_permissions_updated",
        actor_uid=current_user.uid,
        entity_type="user",
        entity_id=uid,
        before={"source_permissions": old_perms},
        after={"source_permissions": new_perms},
    )

    return {
        "status": "ok",
        "uid": uid,
        "source_permissions": new_perms,
    }


# ===================================================================
#  CATEGORY MANAGEMENT
# ===================================================================

@router.get("/categories", summary="List all categories")
async def list_categories(
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all categories in the tenant."""
    fs = _fs(current_user)
    categories = fs.list_categories()
    return {"categories": categories}


@router.post("/categories", summary="Create a category", status_code=201)
async def create_category(
    body: CreateCategoryRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new category in Firestore."""
    fs = _fs(current_user)
    cat_id = str(uuid.uuid4())

    result = fs.create_category(
        category_id=cat_id,
        name=body.name,
        description=body.description,
    )

    fs.create_audit_event(
        event_type="category.created",
        actor_uid=current_user.uid,
        entity_type="category",
        entity_id=cat_id,
        after={"name": body.name, "description": body.description},
    )

    return result


@router.delete("/categories/{cat_id}", summary="Delete a category")
async def delete_category(
    cat_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete a category from Firestore."""
    fs = _fs(current_user)

    existing = fs.get_category(cat_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Category {cat_id} not found")

    fs.delete_category(cat_id)

    fs.create_audit_event(
        event_type="category.deleted",
        actor_uid=current_user.uid,
        entity_type="category",
        entity_id=cat_id,
        before={"name": existing.get("name", "")},
    )

    return {"status": "ok", "deleted": cat_id}


# ===================================================================
#  DOCUMENT MANAGEMENT
# ===================================================================

@router.put(
    "/documents/{doc_id}/classification",
    summary="Update document classification level",
)
async def update_doc_classification(
    doc_id: str,
    body: UpdateClassificationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update classification_level in Firestore and sync to Postgres chunks."""
    fs = _fs(current_user)

    existing = fs.get_document(doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    old_level = existing.get("classification_level", 1)

    # 1. Update Firestore
    fs.update_document(doc_id, {"classification_level": body.classification_level})

    # 2. Sync to Postgres chunks
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    rows = sync_doc_policy(
        doc_id,
        tenant_id,
        db,
        classification_level=body.classification_level,
        category_ids=existing.get("category_ids", []),
    )
    
    db.commit()

    # 3. Audit log
    fs.create_audit_event(
        event_type="document.classification_updated",
        actor_uid=current_user.uid,
        entity_type="document",
        entity_id=doc_id,
        before={"classification_level": old_level},
        after={"classification_level": body.classification_level},
    )

    return {
        "status": "ok",
        "doc_id": doc_id,
        "classification_level": body.classification_level,
        "chunks_updated": rows,
    }


@router.put(
    "/documents/bulk-categorize",
    summary="Assign categories to multiple documents",
)
async def bulk_categorize_docs(
    body: BulkCategorizeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Assign category_ids to multiple documents + sync to Postgres."""
    fs = _fs(current_user)
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID

    results: List[Dict[str, Any]] = []

    for doc_id in body.doc_ids:
        existing = fs.get_document(doc_id)
        if not existing:
            results.append({"doc_id": doc_id, "status": "not_found"})
            continue

        old_cats = existing.get("category_ids", [])

        # 1. Update Firestore
        fs.update_document(doc_id, {"category_ids": body.category_ids})

        # 2. Sync to Postgres chunks
        rows = sync_doc_policy(
            doc_id,
            tenant_id,
            db,
            classification_level=existing.get("classification_level", 1),
            category_ids=body.category_ids,
        )

        # 3. Audit log
        fs.create_audit_event(
            event_type="document.categories_updated",
            actor_uid=current_user.uid,
            entity_type="document",
            entity_id=doc_id,
            before={"category_ids": old_cats},
            after={"category_ids": body.category_ids},
        )

        results.append({
            "doc_id": doc_id,
            "status": "ok",
            "chunks_updated": rows,
        })

    db.commit()

    return {"status": "ok", "results": results}


@router.delete("/documents/{doc_id}", summary="Soft-delete a document")
async def soft_delete_document(
    doc_id: str,
    body: SoftDeleteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft-delete a document (sets deleted_at, deleted_by_uid, delete_reason)."""
    fs = _fs(current_user)

    existing = fs.get_document(doc_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    fs.soft_delete_document(
        doc_id,
        deleted_by_uid=current_user.uid,
        reason=body.reason,
    )

    fs.create_audit_event(
        event_type="document.soft_deleted",
        actor_uid=current_user.uid,
        entity_type="document",
        entity_id=doc_id,
        before={"status": existing.get("status", "active")},
        after={"status": "deleted", "reason": body.reason},
    )

    return {"status": "ok", "doc_id": doc_id}


# ===================================================================
#  AUDIT LOG
# ===================================================================

@router.get("/audit-log", summary="Paginated audit log")
async def get_audit_log(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return paginated audit events, ordered by created_at desc."""
    fs = _fs(current_user)
    events = fs.list_audit_events(limit=limit, offset=offset)
    return {"events": events, "limit": limit, "offset": offset}

"""
Firestore service for document metadata and multi-tenant data management.

Handles all Firestore CRUD operations for:
- Documents metadata
- Categories
- Users  
- Audit events
- Ingestion cursors
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from google.cloud.firestore_v1 import FieldFilter
from src.utils.firebase import firestore_client
from config.settings import DEFAULT_TENANT_ID

logger = logging.getLogger(__name__)


class FirestoreService:
    """Service for managing Firestore collections with typed CRUD methods."""
    
    def __init__(self, tenant_id: str = DEFAULT_TENANT_ID):
        self.tenant_id = tenant_id
        self.db = firestore_client
    
    # ==================== DOCUMENTS ====================
    
    def create_document(
        self,
        doc_id: str,
        title: str,
        source_type: str,
        source_metadata: Dict[str, Any],
        *,
        classification_level: int = 1,
        category_ids: List[str] = None,
        entity_name: str = "",
        document_type: str = "",
        period: str = "",
        s3_url: str = "",
        normalized_url: str = "",
        confidence: float = 0.0,
        created_by_uid: str = "",
        status: str = "active",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new document in Firestore.
        
        Args:
            doc_id: Unique document ID
            title: Document title/filename
            source_type: Source type (local, s3, sharepoint, gdrive)
            source_metadata: Source-specific metadata (e.g., s3_key, etag, etc.)
            classification_level: Security clearance level (0-3)
            category_ids: List of category IDs
            entity_name: Entity name extracted from document
            document_type: Document type (e.g., "Invoice", "Contract")
            period: Period/date extracted from document
            s3_url: S3 URL of source PDF
            normalized_url: S3 URL of normalized JSON
            confidence: Extraction confidence score
            created_by_uid: UID of user who created this document
            status: Document status (active, deleted, processing)
            **kwargs: Additional custom fields
        """
        doc_data = {
            "title": title,
            "source_type": source_type,
            "source_metadata": source_metadata or {},
            "classification_level": classification_level,
            "category_ids": category_ids or [],
            "entity_name": entity_name,
            "document_type": document_type,
            "period": period,
            "s3_url": s3_url,
            "normalized_url": normalized_url,
            "confidence": confidence,
            "status": status,
            "created_by_uid": created_by_uid,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
            "deleted_by": None,
            "deleted_reason": None,
            "stats": {
                "chunks_count": 0,
                "file_size_bytes": 0,
            },
            **kwargs
        }
        
        doc_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("documents")
            .document(doc_id)
        )
        doc_ref.set(doc_data)
        logger.info(f"Created document {doc_id} in tenant {self.tenant_id}")
        return {**doc_data, "id": doc_id}
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        doc_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("documents")
            .document(doc_id)
        )
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> None:
        """Update document fields."""
        updates["updated_at"] = datetime.utcnow()
        doc_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("documents")
            .document(doc_id)
        )
        doc_ref.update(updates)
        logger.info(f"Updated document {doc_id}")
    
    def soft_delete_document(
        self,
        doc_id: str,
        deleted_by_uid: str,
        reason: str = ""
    ) -> None:
        """Soft delete a document."""
        self.update_document(doc_id, {
            "status": "deleted",
            "deleted_at": datetime.utcnow(),
            "deleted_by": deleted_by_uid,
            "deleted_reason": reason,
        })
        logger.info(f"Soft deleted document {doc_id}")
    
    def list_documents(
        self,
        *,
        status: str = "active",
        source_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List documents with filtering."""
        try:
            query = (
                self.db.collection("tenants")
                .document(self.tenant_id)
                .collection("documents")
                .where(filter=FieldFilter("status", "==", status))
            )
            
            if source_type:
                query = query.where(filter=FieldFilter("source_type", "==", source_type))
            
            query = query.order_by("created_at", direction="DESCENDING")
            query = query.limit(limit).offset(offset)
            
            docs = query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            return results
        except Exception as exc:
            # If composite index is missing, fall back to unordered query
            if "index" in str(exc).lower():
                logger.warning(
                    "Firestore composite index missing, falling back to unordered query. "
                    "Create the index at the URL in the error above to fix this."
                )
                query = (
                    self.db.collection("tenants")
                    .document(self.tenant_id)
                    .collection("documents")
                    .where(filter=FieldFilter("status", "==", status))
                )
                if source_type:
                    query = query.where(filter=FieldFilter("source_type", "==", source_type))
                query = query.limit(limit)
                docs = query.stream()
                results = []
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    results.append(data)
                # Sort in Python as fallback
                results.sort(
                    key=lambda d: d.get("created_at", ""),
                    reverse=True,
                )
                return results
            raise
    
    def get_document_by_source(
        self,
        source_type: str,
        source_key: str,
        source_value: Any
    ) -> Optional[Dict[str, Any]]:
        """Find document by source metadata (for idempotency checks).
        
        Example:
            get_document_by_source("s3", "s3_key", "datalake/invoice.pdf")
        """
        query = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("documents")
            .where(filter=FieldFilter("source_type", "==", source_type))
            .where(filter=FieldFilter(f"source_metadata.{source_key}", "==", source_value))
            .limit(1)
        )
        
        docs = list(query.stream())
        if docs:
            data = docs[0].to_dict()
            data["id"] = docs[0].id
            return data
        return None
    
    def count_documents(self, status: str = "active") -> int:
        """Count documents by status."""
        query = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("documents")
            .where(filter=FieldFilter("status", "==", status))
        )
        return len(list(query.stream()))
    
    # ==================== CATEGORIES ====================
    
    def create_category(self, category_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new category."""
        cat_data = {
            "name": name,
            "created_at": datetime.utcnow(),
            **kwargs
        }
        cat_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("categories")
            .document(category_id)
        )
        cat_ref.set(cat_data)
        return {**cat_data, "id": category_id}
    
    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get a category by ID."""
        cat_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("categories")
            .document(category_id)
        )
        doc = cat_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None
    
    def list_categories(self) -> List[Dict[str, Any]]:
        """List all categories."""
        cats = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("categories")
            .stream()
        )
        results = []
        for cat in cats:
            data = cat.to_dict()
            data["id"] = cat.id
            results.append(data)
        return results
    
    def delete_category(self, category_id: str) -> None:
        """Delete a category."""
        cat_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("categories")
            .document(category_id)
        )
        cat_ref.delete()
        logger.info(f"Deleted category {category_id}")
    
    # ==================== USERS ====================
    
    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get a user by UID."""
        user_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("users")
            .document(uid)
        )
        doc = user_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["uid"] = doc.id
            return data
        return None
    
    def update_user(self, uid: str, updates: Dict[str, Any]) -> None:
        """Update user fields."""
        updates["updated_at"] = datetime.utcnow()
        user_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("users")
            .document(uid)
        )
        user_ref.update(updates)
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users in the tenant."""
        users_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("users")
            .stream()
        )
        results = []
        for doc in users_ref:
            data = doc.to_dict()
            data["uid"] = doc.id
            results.append(data)
        return results
    
    # ==================== AUDIT EVENTS ====================
    
    def create_audit_event(
        self,
        event_type: str,
        actor_uid: str,
        entity_type: str,
        entity_id: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create an audit event."""
        event_data = {
            "event_type": event_type,
            "actor_uid": actor_uid,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "before": before or {},
            "after": after or {},
            "created_at": datetime.utcnow(),
        }
        event_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("audit_events")
            .document()
        )
        event_ref.set(event_data)
        logger.info(f"Created audit event: {event_type} by {actor_uid}")
        return event_ref.id
    
    def list_audit_events(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List audit events, ordered by created_at desc."""
        query = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("audit_events")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .offset(offset)
        )
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        return results
    
    # ==================== INGESTION CURSORS ====================
    
    def get_cursor(self, source_key: str) -> Optional[Dict[str, Any]]:
        """Get an ingestion cursor by source key.
        
        Args:
            source_key: Unique key (e.g., "s3:bucket:prefix", "sharepoint:site:drive")
        
        Returns:
            Cursor data or None if not found (indicates first sync)
        """
        cursor_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("ingestion_cursors")
            .document(source_key)
        )
        doc = cursor_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["source_key"] = doc.id
            return data
        return None
    
    def set_cursor(
        self,
        source_key: str,
        source_type: str,
        cursor_value: str,
    ) -> None:
        """Set or update an ingestion cursor.
        
        Args:
            source_key: Unique key
            source_type: Source type (s3, sharepoint, gdrive)
            cursor_value: Cursor value (deltaLink, continuation token, etc.)
        """
        cursor_data = {
            "source_type": source_type,
            "cursor_key": source_key,
            "cursor_value": cursor_value,
            "updated_at": datetime.utcnow(),
        }
        cursor_ref = (
            self.db.collection("tenants")
            .document(self.tenant_id)
            .collection("ingestion_cursors")
            .document(source_key)
        )
        cursor_ref.set(cursor_data)
        logger.info(f"Updated cursor {source_key}")

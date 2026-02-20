from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.base import get_db
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from config.settings import DEFAULT_TENANT_ID
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics from Firestore (documents) and Postgres (chunks)."""
    try:
        now = datetime.utcnow()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = start_of_today - timedelta(days=now.weekday())

        # Document stats from Firestore (source of truth for metadata)
        firestore_svc = FirestoreService(tenant_id=DEFAULT_TENANT_ID)
        all_docs = firestore_svc.list_documents(status="active", limit=10000)
        total_docs = len(all_docs)
        docs_today = sum(1 for doc in all_docs if doc.get("created_at") and doc["created_at"] >= start_of_today)
        docs_this_week = sum(1 for doc in all_docs if doc.get("created_at") and doc["created_at"] >= start_of_week)
        unique_entities = len(set(doc.get("entity_name", "") for doc in all_docs if doc.get("entity_name")))

        # Chunk count from Postgres (pgvector)
        total_chunks = db.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.tenant_id == DEFAULT_TENANT_ID
        ).scalar() or 0

        return {
            "total_documents": total_docs,
            "documents_today": docs_today,
            "documents_this_week": docs_this_week,
            "total_chunks": total_chunks,
            "unique_entities": unique_entities,
            "system_status": "OPTIMAL"
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

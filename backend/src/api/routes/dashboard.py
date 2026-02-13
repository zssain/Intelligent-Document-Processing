from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.base import get_db
from src.database.models import Document, DocumentChunk
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics based on real data."""
    try:
        now = datetime.utcnow()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = start_of_today - timedelta(days=now.weekday())

        total_docs = db.query(func.count(Document.id)).scalar()
        docs_today = db.query(func.count(Document.id)).filter(Document.processed_at >= start_of_today).scalar()
        docs_this_week = db.query(func.count(Document.id)).filter(Document.processed_at >= start_of_week).scalar()

        # Growth calculation (mocking for now as we might not have yesterday's data easily without more queries)
        # But let's just return what was requested
        
        total_chunks = db.query(func.count(DocumentChunk.id)).scalar()
        unique_entities = db.query(func.count(func.distinct(Document.entity))).scalar()
        
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

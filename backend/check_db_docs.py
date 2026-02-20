"""Check database documents for S3 URLs."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.base import SessionLocal
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from config.settings import DEFAULT_TENANT_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_db_documents():
    """List documents from Firestore and chunk counts from Postgres."""
    db = SessionLocal()
    try:
        fs = FirestoreService(tenant_id=DEFAULT_TENANT_ID)
        documents = fs.list_documents(status="active", limit=100)
        logger.info(f"Found {len(documents)} documents in Firestore")
        
        for doc in documents:
            doc_id = doc.get("id", "?")
            chunk_count = db.query(DocumentChunk).filter(
                DocumentChunk.doc_id == doc_id
            ).count()
            logger.info(f"  - {doc.get('title', 'untitled')} (ID: {doc_id})")
            logger.info(f"    Chunks: {chunk_count}")
            logger.info("-" * 20)
            
        return True
    except Exception as e:
        logger.error(f"Error checking DB: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_db_documents()

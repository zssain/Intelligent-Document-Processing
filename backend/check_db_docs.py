"""Check database documents for S3 URLs."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.base import SessionLocal
from src.database.models import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_db_documents():
    """List documents in DB and their S3 status."""
    db = SessionLocal()
    try:
        documents = db.query(Document).all()
        logger.info(f"Found {len(documents)} documents in database")
        
        for doc in documents:
            logger.info(f"  - {doc.filename} (ID: {doc.id})")
            logger.info(f"    S3 URL: {doc.s3_url}")
            logger.info(f"    File Size: {doc.file_size_bytes} bytes")
            logger.info(f"    Processed At: {doc.processed_at}")
            logger.info("-" * 20)
            
        return True
    except Exception as e:
        logger.error(f"Error checking DB: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_db_documents()

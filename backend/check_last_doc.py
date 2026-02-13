"""Check last document in DB for S3 paths."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.base import SessionLocal
from src.database.models import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_last_doc():
    db = SessionLocal()
    try:
        doc = db.query(Document).order_by(Document.processed_at.desc()).first()
        if doc:
            logger.info(f"Last Document: {doc.filename} (ID: {doc.id})")
            logger.info(f"  S3 URL: {doc.s3_url}")
            logger.info(f"  Raw Path: {doc.raw_cu_output_path}")
            logger.info(f"  Normalized Path: {doc.normalized_output_path}")
        else:
            logger.info("No documents found")
    finally:
        db.close()

if __name__ == "__main__":
    check_last_doc()

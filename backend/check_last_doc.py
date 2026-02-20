"""Check last document in DB for S3 paths."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.firestore_service import FirestoreService
from config.settings import DEFAULT_TENANT_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_last_doc():
    try:
        fs = FirestoreService(tenant_id=DEFAULT_TENANT_ID)
        docs = fs.list_documents(status="active", limit=1)
        if docs:
            doc = docs[0]
            logger.info(f"Last Document: {doc.get('title', 'untitled')} (ID: {doc.get('id')})")
            logger.info(f"  S3 URL: {doc.get('s3_url', '')}")
            logger.info(f"  Normalized URL: {doc.get('normalized_url', '')}")
        else:
            logger.info("No documents found")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    check_last_doc()

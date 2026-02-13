"""Comprehensive test for full S3 migration."""

import sys
import os
import requests
import json
import time
import logging

sys.path.insert(0, os.path.dirname(__file__))

from src.storage.s3_service import S3Service
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

def test_full_s3_migration():
    """Verify end-to-end S3 migration of all artifacts."""
    test_pdf = "migration_test.pdf"
    original_pdf = "/home/kanke/projects/bluetide/backend/data/raw/da72e40b_11.pdf"
    
    try:
        s3 = S3Service()
        
        # 1. Prepare valid PDF
        import shutil
        shutil.copy(original_pdf, test_pdf)
        
        logger.info(f"Step 1: Ingesting document {test_pdf}...")
        with open(test_pdf, "rb") as f:
            files = {"file": (test_pdf, f, "application/pdf")}
            response = requests.post(f"{BASE_URL}/rag/ingest", files=files)
            
        if response.status_code != 200:
            logger.error(f"Ingest failed: {response.text}")
            return False
            
        data = response.json()
        doc_id = data["document_id"]
        logger.info(f"✅ Ingest success. Doc ID: {doc_id}")
        
        # 2. Verify in S3
        logger.info("Step 2: Verifying artifacts in S3...")
        # We need to find the files. Since we use unique prefixes, we'll list the bucket.
        objects = s3.s3_client.list_objects_v2(Bucket=s3.bucket_name)
        
        found_pdf = False
        found_raw = False
        found_normalized = False
        
        if 'Contents' in objects:
            for obj in objects['Contents']:
                key = obj['Key']
                if test_pdf in key: found_pdf = True
                if key.endswith("_raw.json") and test_pdf.replace(".pdf", "") in key: found_raw = True
                if key.endswith("_normalized.json") and test_pdf.replace(".pdf", "") in key: found_normalized = True
                
        if found_pdf and found_raw and found_normalized:
            logger.info("✅ SUCCESS: All 3 artifacts (PDF, Raw, Normalized) found in S3!")
        else:
            logger.error(f"❌ FAILURE: Missing artifacts. PDF: {found_pdf}, Raw: {found_raw}, Normalized: {found_normalized}")
            return False
            
        # 3. Test Deletion
        logger.info(f"Step 3: Deleting document {doc_id}...")
        del_response = requests.delete(f"{BASE_URL}/cu/documents/{doc_id}")
        
        if del_response.status_code != 200:
            logger.error(f"Deletion failed: {del_response.text}")
            return False
            
        logger.info("✅ Deletion API call success.")
        
        # 4. Verify S3 cleanup
        logger.info("Step 4: Verifying S3 cleanup...")
        time.sleep(2) # Brief wait for S3 consistency
        objects = s3.s3_client.list_objects_v2(Bucket=s3.bucket_name)
        
        still_exists = []
        if 'Contents' in objects:
            for obj in objects['Contents']:
                key = obj['Key']
                if test_pdf.replace(".pdf", "") in key:
                    still_exists.append(key)
                    
        if not still_exists:
            logger.info("✅ SUCCESS: All artifacts cleaned up from S3!")
            return True
        else:
            logger.error(f"❌ FAILURE: Files still exist in S3: {still_exists}")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False
    finally:
        if os.path.exists("migration_test.pdf"):
            os.remove("migration_test.pdf")

if __name__ == "__main__":
    # Ensure backend is running!
    success = test_full_s3_migration()
    sys.exit(0 if success else 1)

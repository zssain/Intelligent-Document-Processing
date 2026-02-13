"""Test S3 presigned URL generation and access."""

import sys
import os
import requests
sys.path.insert(0, os.path.dirname(__file__))

from src.storage.s3_service import S3Service
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_presigned_url():
    """Test generating and accessing a presigned URL."""
    try:
        s3_service = S3Service()
        
        # 1. List objects to find one to test with
        logger.info("Listing objects in S3...")
        response = s3_service.s3_client.list_objects_v2(
            Bucket=s3_service.bucket_name,
            MaxKeys=1
        )
        
        if 'Contents' not in response:
            logger.error("No objects found in bucket to test with. Please upload a file first.")
            return False
            
        test_key = response['Contents'][0]['Key']
        logger.info(f"Testing with key: {test_key}")
        
        # 2. Generate presigned URL
        logger.info("Generating presigned URL...")
        presigned_url = s3_service.generate_presigned_url(test_key)
        logger.info(f"Generated URL: {presigned_url}")
        
        # 3. Attempt to access the URL
        logger.info("Accessing URL via GET...")
        res = requests.get(presigned_url)
        
        if res.status_code == 200:
            logger.info("✅ SUCCESS: Presigned URL is accessible!")
            return True
        else:
            logger.error(f"❌ FAILURE: Received status code {res.status_code}")
            logger.error(f"Response body: {res.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_presigned_url()
    sys.exit(0 if success else 1)

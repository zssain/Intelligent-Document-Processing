"""Test S3 connection and upload."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.storage.s3_service import S3Service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_s3_connection():
    """Test S3 service initialization and basic operations."""
    try:
        # Initialize S3 service
        logger.info("Initializing S3 service...")
        s3_service = S3Service()
        logger.info("✓ S3 service initialized successfully")
        
        # Test bucket access
        logger.info(f"Testing access to bucket: {s3_service.bucket_name}")
        response = s3_service.s3_client.head_bucket(Bucket=s3_service.bucket_name)
        logger.info(f"✓ Bucket accessible: {response['ResponseMetadata']['HTTPStatusCode']}")
        
        # List objects (just to verify permissions)
        logger.info("Testing list objects permission...")
        response = s3_service.s3_client.list_objects_v2(
            Bucket=s3_service.bucket_name,
            MaxKeys=1
        )
        logger.info(f"✓ List objects successful. Objects in bucket: {response.get('KeyCount', 0)}")
        
        logger.info("\n✅ All S3 tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ S3 test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_s3_connection()
    sys.exit(0 if success else 1)

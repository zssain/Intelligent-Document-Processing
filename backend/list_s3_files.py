"""Check S3 bucket contents."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.storage.s3_service import S3Service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_s3_files():
    """List all files in the S3 bucket."""
    try:
        s3_service = S3Service()
        bucket_name = s3_service.bucket_name
        
        logger.info(f"Listing files in bucket: {bucket_name}")
        
        response = s3_service.s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=s3_service.prefix
        )
        
        if 'Contents' in response:
            logger.info(f"\n✅ Found {len(response['Contents'])} files:")
            for obj in response['Contents']:
                size_mb = obj['Size'] / (1024 * 1024)
                logger.info(f"  - {obj['Key']} ({size_mb:.2f} MB) - {obj['LastModified']}")
        else:
            logger.info("\n⚠️  No files found in bucket")
            logger.info(f"Prefix: {s3_service.prefix}")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Failed to list files: {e}")
        return False

if __name__ == "__main__":
    success = list_s3_files()
    sys.exit(0 if success else 1)

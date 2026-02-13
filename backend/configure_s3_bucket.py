"""Configure S3 bucket for public read access."""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from src.storage.s3_service import S3Service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configure_bucket_public_access():
    """Configure S3 bucket to allow public read access to PDFs."""
    try:
        s3_service = S3Service()
        bucket_name = s3_service.bucket_name
        
        logger.info(f"Configuring public access for bucket: {bucket_name}")
        
        # Bucket policy to allow public read access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        # Apply the bucket policy
        s3_service.s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        logger.info("✓ Bucket policy applied successfully")
        
        # Disable Block Public Access settings
        try:
            s3_service.s3_client.delete_public_access_block(Bucket=bucket_name)
            logger.info("✓ Public access block removed")
        except Exception as e:
            logger.warning(f"Could not remove public access block: {e}")
            logger.info("You may need to manually disable 'Block all public access' in AWS Console")
        
        logger.info("\n✅ Bucket configured for public access!")
        logger.info(f"PDFs uploaded to {bucket_name} will be publicly accessible")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Configuration failed: {e}")
        logger.info("\nPlease manually configure the bucket in AWS Console:")
        logger.info("1. Go to S3 bucket settings")
        logger.info("2. Disable 'Block all public access'")
        logger.info("3. Add the bucket policy shown above")
        return False

if __name__ == "__main__":
    success = configure_bucket_public_access()
    sys.exit(0 if success else 1)

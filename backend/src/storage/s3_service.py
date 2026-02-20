"""AWS S3 service for document storage.

Supports both explicit IAM key auth and implicit IAM role auth (EC2 / ECS / Lambda).
When AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are empty the SDK falls back to the
default credential chain (instance profile, env, config file, etc.).
"""

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from config.settings import settings
import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class S3Service:
    """Service for uploading and managing PDFs in AWS S3."""
    
    def __init__(self):
        """Initialize S3 client with credentials from settings.

        If aws_access_key_id / aws_secret_access_key are empty strings the
        keys are **not** passed to boto3 so it can fall back to IAM role auth.
        """
        try:
            # Explicitly use SigV4 and virtual addressing for S3
            s3_config = Config(
                signature_version='s3v4',
                region_name=settings.aws_region,
                s3={'addressing_style': 'virtual'}
            )

            # Build kwargs – omit keys when empty so IAM role auth works
            client_kwargs: dict = dict(
                region_name=settings.aws_region,
                endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
                config=s3_config,
            )
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

            self.s3_client = boto3.client('s3', **client_kwargs)
            self.bucket_name = settings.aws_s3_bucket_name
            self.prefix = settings.s3_pdf_prefix
            logger.info(f"S3 service initialized for bucket: {self.bucket_name} in {settings.aws_region}")

            # Fail-fast: validate bucket is reachable and region matches
            self._validate_bucket()
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise

    # ── Validation ────────────────────────────────────────────────────────
    def _validate_bucket(self) -> None:
        """HeadBucket check – surfaces region/permission mismatches early."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' is accessible")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "301":
                raise RuntimeError(
                    f"Bucket '{self.bucket_name}' exists in a DIFFERENT region. "
                    f"Set AWS_REGION to the correct region (current: {settings.aws_region})."
                ) from e
            if code in ("403", "AccessDenied"):
                logger.warning(
                    f"HeadBucket returned 403 for '{self.bucket_name}'. "
                    "Credentials may lack s3:ListBucket. Continuing optimistically."
                )
            else:
                raise

    # ── Listing & metadata ────────────────────────────────────────────────
    def list_objects(self, prefix: str, max_keys: int = 1000) -> List[Dict]:
        """List objects under *prefix* using the list_objects_v2 paginator.

        Returns a list of dicts with keys: ``key``, ``etag``, ``last_modified``,
        ``size``.  Folder placeholder keys (ending with ``/``) are omitted.
        """
        results: List[Dict] = []
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iter = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={"MaxItems": max_keys},
            )
            for page in page_iter:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue  # skip folder placeholders
                    results.append({
                        "key": key,
                        "etag": obj["ETag"].strip('"'),
                        "last_modified": obj["LastModified"].isoformat(),
                        "size": obj["Size"],
                    })
            logger.info(f"Listed {len(results)} objects under prefix '{prefix}'")
        except ClientError as e:
            logger.error(f"Failed to list objects under '{prefix}': {e}")
            raise
        return results

    def head_object(self, key: str) -> Dict:
        """Return metadata dict for a single S3 object."""
        try:
            resp = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                "key": key,
                "etag": resp["ETag"].strip('"'),
                "last_modified": resp["LastModified"].isoformat(),
                "size": resp["ContentLength"],
                "content_type": resp.get("ContentType", ""),
            }
        except ClientError as e:
            logger.error(f"head_object failed for '{key}': {e}")
            raise

    def download_to_tempfile(self, key: str) -> str:
        """Download an S3 object to a local temp file and return its path.

        Caller is responsible for deleting the temp file after use.
        """
        suffix = os.path.splitext(key)[1] or ".bin"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            self.s3_client.download_file(self.bucket_name, key, tmp_path)
            logger.info(f"Downloaded s3://{self.bucket_name}/{key} -> {tmp_path}")
            return tmp_path
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            logger.error(f"Failed to download '{key}': {e}")
            raise
    
    def upload_pdf(self, file_path: str, original_filename: str) -> Optional[str]:
        """Upload a PDF file to S3."""
        try:
            unique_id = uuid.uuid4().hex[:8]
            s3_key = f"{self.prefix}{unique_id}_{original_filename}"
            
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'application/pdf',
                        'Metadata': {
                            'original-filename': original_filename,
                            'file-size': str(file_size)
                        }
                    }
                )
            
            s3_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            logger.info(f"Successfully uploaded {original_filename} to S3: {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"S3 PDF upload failed: {e}")
            return None

    def upload_json(self, json_data: str, filename: str, folder: str = "processed/raw/") -> Optional[str]:
        """
        Upload JSON string data directly to S3.
        
        Args:
            json_data: JSON string content
            filename: Target filename in S3
            folder: Subfolder prefix (e.g. 'processed/raw/')
            
        Returns:
            Full S3 URL of the uploaded JSON
        """
        try:
            s3_key = f"{folder}{filename}"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json'
            )
            
            s3_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            logger.info(f"Successfully uploaded JSON to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"S3 JSON upload failed for {filename}: {e}")
            return None

    def download_json(self, s3_url_or_key: str) -> Optional[dict]:
        """Download and parse a JSON file from S3.

        Args:
            s3_url_or_key: Full S3 URL or key to the JSON file

        Returns:
            Parsed dict or None on failure
        """
        import json as _json
        try:
            s3_key = s3_url_or_key
            if s3_url_or_key.startswith("http"):
                extracted = self.get_key_from_url(s3_url_or_key)
                if extracted:
                    s3_key = extracted
                else:
                    return None

            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return _json.loads(obj["Body"].read())
        except Exception as e:
            logger.debug(f"download_json failed for {s3_url_or_key}: {e}")
            return None

    def delete_by_key(self, s3_key: str) -> bool:
        """Delete an object from S3 by its key."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted S3 object: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 object {s3_key}: {e}")
            return False

    def get_key_from_url(self, s3_url: str) -> Optional[str]:
        """Extract S3 key from a full S3 URL."""
        if not s3_url:
            return None
            
        try:
            # Handle standard virtual hosted style
            prefixes = [
                f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/",
                f"https://{self.bucket_name}.s3-{settings.aws_region}.amazonaws.com/",
                f"https://{self.bucket_name}.s3.amazonaws.com/",
                f"https://s3.{settings.aws_region}.amazonaws.com/{self.bucket_name}/"
            ]
            
            for prefix in prefixes:
                if s3_url.startswith(prefix):
                    key = s3_url.split(prefix)[1]
                    logger.debug(f"Extracted key '{key}' from URL '{s3_url}' using prefix '{prefix}'")
                    return key
            
            # Fallback: find the first slash after .com/
            if ".amazonaws.com/" in s3_url:
                parts = s3_url.split(".amazonaws.com/")
                if len(parts) > 1:
                    path_part = parts[1]
                    # If it's a path-style URL (s3.region.amazonaws.com/bucket/key)
                    if path_part.startswith(f"{self.bucket_name}/"):
                        key = path_part.split(f"{self.bucket_name}/")[1]
                        return key
                    return path_part
            
            logger.warning(f"Could not extract key from S3 URL: {s3_url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting key from URL {s3_url}: {e}")
            return None

    def delete_object(self, s3_url_or_key: str) -> bool:
        """
        Delete an object from S3.
        
        Args:
            s3_url_or_key: Full S3 URL OR key of the object to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            s3_key = s3_url_or_key
            if s3_url_or_key.startswith("http"):
                s3_key = self.get_key_from_url(s3_url_or_key)
                
            if not s3_key:
                logger.warning(f"No S3 key found for deletion: {s3_url_or_key}")
                return False
                
            return self.delete_by_key(s3_key)
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False

    def generate_presigned_url(self, s3_key_or_url: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to a private S3 object.
        
        Args:
            s3_key_or_url: S3 key OR full S3 URL of the object
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL or None if generation fails
        """
        try:
            s3_key = s3_key_or_url
            # If it looks like a URL, try to extract the key
            if s3_key_or_url.startswith("http"):
                extracted_key = self.get_key_from_url(s3_key_or_url)
                if extracted_key:
                    s3_key = extracted_key
                else:
                    logger.warning(f"Could not extract key from URL: {s3_key_or_url}, using as is")

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL for {s3_key}: {e}")
            return None


__all__ = ["S3Service"]

import os
import aiofiles
import json
import uuid
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DocumentStorage:
    """Handles physical storage and retrieval of document files."""
    
    @staticmethod
    async def save_upload(file_content: bytes, original_filename: str) -> str:
        """Saves an uploaded file and returns the path."""
        os.makedirs(settings.upload_dir, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{unique_id}_{original_filename}"
        file_path = os.path.join(settings.upload_dir, filename)
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
            
        logger.info(f"File saved to storage: {file_path}")
        return file_path

    @staticmethod
    async def save_json(data: dict, prefix: str, original_filename: str) -> str:
        """Saves JSON data and returns the path."""
        os.makedirs(settings.processed_dir, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        base_name = os.path.splitext(original_filename)[0]
        filename = f"{prefix}_{unique_id}_{base_name}.json"
        file_path = os.path.join(settings.processed_dir, filename)
        
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2))
            
        logger.info(f"JSON data saved to storage: {file_path}")
        return file_path

    @staticmethod
    def get_raw_storage_path(filename: str) -> str:
        return os.path.join(settings.upload_dir, filename)

    @staticmethod
    def get_processed_storage_path(filename: str) -> str:
        return os.path.join(settings.processed_dir, filename)

    @staticmethod
    def delete_file(file_path: str):
        """Removes a file from physical storage if it exists."""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"File deleted from storage: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")

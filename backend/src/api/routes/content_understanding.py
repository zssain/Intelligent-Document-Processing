from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from typing import List
from sqlalchemy.orm import Session
from src.database.base import get_db
from src.database.models import Document
from src.cu.client import ContentUnderstandingService
from config.settings import settings
import os
import uuid
import logging
import json
from datetime import datetime
import aiofiles
from src.storage.documents import DocumentStorage
from src.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

from pydantic import BaseModel

router = APIRouter()

class BatchDeleteRequest(BaseModel):
    document_ids: List[str]

# Initialize Content Understanding service
try:
    cu_service = ContentUnderstandingService()
except Exception as e:
    logger.error(f"Failed to initialize Content Understanding service: {e}")
    cu_service = None

# Initialize S3 service
try:
    s3_service = S3Service()
except Exception as e:
    logger.error(f"Failed to initialize S3 service: {e}")
    s3_service = None


@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """Analyze a document using Azure AI Content Understanding."""
    if cu_service is None:
        raise HTTPException(
            status_code=500,
            detail="Content Understanding service is not available. Please check configuration."
        )
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Save uploaded file using Storage Service
        content = await file.read()
        file_path = await DocumentStorage.save_upload(content, file.filename)
        
        # Calculate file size
        file_size_bytes = os.path.getsize(file_path)
        
        # Upload to S3
        s3_url = None
        if s3_service:
            try:
                s3_url = s3_service.upload_pdf(file_path, file.filename)
                if s3_url:
                    logger.info(f"PDF uploaded to S3: {s3_url}")
                else:
                    logger.warning(f"S3 upload returned None for {file.filename}")
            except Exception as s3_error:
                logger.error(f"S3 upload failed (continuing anyway): {s3_error}")
        else:
            logger.warning("S3 service not available, skipping S3 upload")
        
        # Analyze document with Content Understanding
        logger.info(f"Analyzing document with CU analyzer: {settings.azure_cu_analyzer_id}")
        simplified_result = cu_service.analyze_document(file_path)
        
        # Save processed data directly to S3
        raw_s3_url = None
        if s3_service:
            try:
                # Use a unique name for the result file
                base_name = os.path.splitext(file.filename)[0]
                unique_suffix = uuid.uuid4().hex[:6]
                json_filename = f"{base_name}_{unique_suffix}_raw.json"
                
                # Add metadata
                simplified_result["metadata"]["source_file"] = file.filename
                simplified_result["metadata"]["processed_at"] = datetime.utcnow().isoformat()
                
                raw_s3_url = s3_service.upload_json(
                    json.dumps(simplified_result, indent=2), 
                    json_filename, 
                    "processed/raw/"
                )
                logger.info(f"Analysis result uploaded to S3: {raw_s3_url}")
            except Exception as e:
                logger.error(f"Failed to upload analysis result to S3: {e}")
        
        # Cleanup temporary local PDF
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Temporary file removed: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
            
        return {
            "status": "success",
            "filename": file.filename,
            "processed_file_s3": raw_s3_url,
            "result": simplified_result
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze document: {str(e)}"
        )


@router.get("/documents")
async def list_cu_documents(db: Session = Depends(get_db)):
    """List all processed documents from the database."""
    try:
        documents = db.query(Document).order_by(Document.processed_at.desc()).all()
        
        doc_list = []
        for doc in documents:
            doc_list.append({
                "id": str(doc.id),
                "filename": doc.filename,
                "vendor_name": doc.entity, # Mapping entity to vendor_name for frontend compatibility
                "total_amount": doc.metrics.get("total_assets") if doc.metrics else 0, # Fallback or specific metric
                "document_type": doc.document_type,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                "source": (doc.source or "local").lower(),
                "confidence_percentage": int((doc.confidence if doc.confidence is not None else 0.95) * 100),
                "s3_url": s3_service.generate_presigned_url(doc.s3_url) if doc.s3_url and s3_service else doc.s3_url,
                "file_size_bytes": doc.file_size_bytes or 0,
                "file_size_mb": f"{(doc.file_size_bytes or 0) / (1024 * 1024):.2f} MB"
            })
        
        return {
            "status": "success",
            "documents": doc_list,
            "total": len(doc_list)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/documents/batch")
async def delete_documents_batch(request: BatchDeleteRequest, db: Session = Depends(get_db)):
    """Delete multiple documents and their associated chunks."""
    try:
        document_ids = request.document_ids
        doc_uuids = [uuid.UUID(doc_id) for doc_id in document_ids]
        
        # Get files paths for cleanup before deleting from DB
        docs = db.query(Document).filter(Document.id.in_(doc_uuids)).all()
        
        deleted_count = 0
        for doc in docs:
            # Delete from S3 if URLs exist
            if s3_service:
                s3_paths = [doc.s3_url, doc.raw_cu_output_path, doc.normalized_output_path]
                for path in s3_paths:
                    if path and path.startswith("http"):
                        try:
                            s3_service.delete_object(path) # delete_object handles URL or key
                        except Exception as s3_error:
                            logger.error(f"Failed to delete S3 file {path} for {doc.id}: {s3_error}")
            
            # Use db.delete to ensure relationship cascades work (deleting chunks)
            db.delete(doc)
            deleted_count += 1

        db.commit()
        
        return {
            "status": "success", 
            "message": f"Successfully deleted {deleted_count} documents",
            "deleted_count": deleted_count
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="One or more document IDs are invalid")
    except Exception as e:
        logger.error(f"Error in batch delete: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a specific document and its associated chunks."""
    try:
        doc_uuid = uuid.UUID(document_id)
        doc = db.query(Document).filter(Document.id == doc_uuid).first()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Delete from S3 if URLs exist
        if s3_service:
            s3_paths = [doc.s3_url, doc.raw_cu_output_path, doc.normalized_output_path]
            for path in s3_paths:
                if path and path.startswith("http"):
                    try:
                        s3_service.delete_object(path)
                    except Exception as s3_error:
                        logger.error(f"Failed to delete S3 file {path} for {doc.id}: {s3_error}")
            
        db.delete(doc)
        db.commit()
        
        return {"status": "success", "message": f"Document {document_id} deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

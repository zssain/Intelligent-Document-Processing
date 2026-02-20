from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from src.database.base import get_db
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from src.cu.client import ContentUnderstandingService
from src.api.auth import CurrentUser, get_current_user, get_user_doc_filter
from config.settings import settings, DEFAULT_TENANT_ID
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
    """Analyze a document using Azure AI Document Intelligence."""
    if cu_service is None:
        raise HTTPException(
            status_code=500,
            detail="Document Intelligence service is not available. Please check configuration."
        )
    
    ext = os.path.splitext(file.filename or "")[1].lstrip(".").lower()
    if ext not in settings.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '.{ext}'. "
                f"Supported: {', '.join(settings.supported_extensions)}"
            ),
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
        logger.info(f"Analyzing document with backend: {cu_service.model_id}")
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
async def list_cu_documents(
    db: Session = Depends(get_db),
    source_type: str = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """List processed documents from Firestore with RBAC enforcement.

    Admin users see all documents; regular users see only documents matching
    their clearance level and allowed categories.
    """
    try:
        tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
        firestore_svc = FirestoreService(tenant_id=tenant_id)
        documents = firestore_svc.list_documents(
            status="active",
            source_type=source_type,
            limit=1000,
        )

        # ── RBAC filtering ──────────────────────────────────────────
        doc_filter = get_user_doc_filter(current_user)
        if doc_filter is not None:
            user_clearance: int = doc_filter["clearance_level"]
            user_cats: List[str] = doc_filter["allowed_category_ids"]
            visible: List[Dict[str, Any]] = []
            for doc in documents:
                doc_level = doc.get("classification_level", 0)
                doc_cats = doc.get("category_ids", [])
                if doc_level > user_clearance:
                    continue
                if doc_cats and user_cats:
                    if not set(doc_cats).intersection(user_cats):
                        continue
                elif doc_cats and not user_cats:
                    continue
                visible.append(doc)
            documents = visible

        # ── Map language code to display name ────────────────────────
        _LANG_MAP = {
            "ar": "Arabic",
            "en": "English",
            "fr": "French",
            "hi": "Hindi",
            "ur": "Urdu",
        }

        doc_list = []
        for doc in documents:
            stats = doc.get("stats", {})

            # ── Confidence: pass through actual value ─────────────────
            raw_confidence = doc.get("confidence")
            if raw_confidence is not None and float(raw_confidence) > 0:
                confidence_pct = int(float(raw_confidence) * 100)
            else:
                confidence_pct = 0  # truly unknown

            # ── Language: detect from stored data OR content ──────────
            lang_code = doc.get("document_language", "en")

            # Auto-fix: if lang is 'en' but document content is actually Arabic
            if lang_code == "en":
                corrected = False
                # 1) Check filename for Arabic characters
                doc_title = doc.get("title", "")
                if any('\u0600' <= ch <= '\u06FF' for ch in doc_title):
                    lang_code = "ar"
                    corrected = True

                # 2) Check entity_name for Arabic characters
                if not corrected:
                    entity = doc.get("entity_name", "")
                    if any('\u0600' <= ch <= '\u06FF' for ch in entity):
                        lang_code = "ar"
                        corrected = True

                # 3) Check summary for Arabic characters
                if not corrected:
                    summary = doc.get("summary", "")
                    if any('\u0600' <= ch <= '\u06FF' for ch in summary):
                        lang_code = "ar"
                        corrected = True

                # 4) Check the normalized JSON in S3 for Arabic content
                if not corrected and s3_service:
                    normalized_url = doc.get("normalized_url", "")
                    if normalized_url:
                        try:
                            raw = s3_service.download_json(normalized_url)
                            if raw:
                                # Check structured fields and entity
                                all_text = " ".join(str(v) for v in raw.values() if isinstance(v, str))
                                arabic_chars = sum(1 for ch in all_text if '\u0600' <= ch <= '\u06FF')
                                total_alpha = sum(1 for ch in all_text if ch.isalpha())
                                if total_alpha > 0 and (arabic_chars / total_alpha) > 0.3:
                                    lang_code = "ar"
                                    corrected = True
                        except Exception:
                            pass

                # Self-heal: update Firestore so future reads are correct
                if corrected:
                    try:
                        firestore_svc.update_document(doc["id"], {"document_language": lang_code})
                        logger.info("Auto-corrected language to '%s' for doc %s", lang_code, doc["id"])
                    except Exception:
                        pass

            lang_display = _LANG_MAP.get(lang_code, lang_code)

            # ── Preview URL: build an embeddable preview link ─────────
            raw_s3_url = doc.get("s3_url", "")
            preview_url = ""
            if raw_s3_url:
                if "drive.google.com" in raw_s3_url:
                    # Google Drive → embeddable preview
                    preview_url = raw_s3_url.replace("/view", "/preview")
                elif s3_service:
                    presigned = s3_service.generate_presigned_url(raw_s3_url)
                    if presigned:
                        # Wrap in Google Docs Viewer for reliable iframe embedding
                        # (raw S3 presigned URLs get blocked by X-Frame-Options)
                        from urllib.parse import quote
                        preview_url = f"https://docs.google.com/gview?url={quote(presigned, safe='')}&embedded=true"

            doc_list.append({
                "id": doc["id"],
                "filename": doc.get("title", ""),
                "vendor_name": doc.get("entity_name", ""),
                "total_amount": stats.get("total_assets", 0),
                "document_type": doc.get("document_type", ""),
                "document_language": lang_display,
                "processed_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "source": doc.get("source_type", "local").lower(),
                "confidence_percentage": confidence_pct,
                "s3_url": preview_url,
                "file_size_bytes": stats.get("file_size_bytes", 0),
                "file_size_mb": f"{stats.get('file_size_bytes', 0) / (1024 * 1024):.2f} MB",
                "category_ids": doc.get("category_ids", []),
                "classification_level": doc.get("classification_level", 0),
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
    """Soft delete multiple documents and delete their chunks."""
    try:
        document_ids = request.document_ids
        firestore_svc = FirestoreService(tenant_id=DEFAULT_TENANT_ID)
        
        deleted_count = 0
        for doc_id in document_ids:
            # Get document from Firestore
            doc = firestore_svc.get_document(doc_id)
            if not doc:
                logger.warning(f"Document {doc_id} not found in Firestore")
                continue
            
            # Delete from S3 if URLs exist
            if s3_service:
                s3_paths = [doc.get("s3_url"), doc.get("normalized_url")]
                for path in s3_paths:
                    if path and path.startswith("http"):
                        try:
                            s3_service.delete_object(path)
                        except Exception as s3_error:
                            logger.error(f"Failed to delete S3 file {path} for {doc_id}: {s3_error}")
            
            # Soft delete in Firestore
            firestore_svc.soft_delete_document(doc_id, deleted_by_uid="system", reason="batch_delete")
            
            # Delete chunks from Postgres
            db.query(DocumentChunk).filter(
                DocumentChunk.tenant_id == DEFAULT_TENANT_ID,
                DocumentChunk.doc_id == doc_id
            ).delete(synchronize_session=False)
            
            deleted_count += 1

        db.commit()
        
        return {
            "status": "success", 
            "message": f"Successfully deleted {deleted_count} documents",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error in batch delete: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Soft delete a specific document and delete its chunks."""
    try:
        firestore_svc = FirestoreService(tenant_id=DEFAULT_TENANT_ID)
        doc = firestore_svc.get_document(document_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Delete from S3 if URLs exist
        if s3_service:
            s3_paths = [doc.get("s3_url"), doc.get("normalized_url")]
            for path in s3_paths:
                if path and path.startswith("http"):
                    try:
                        s3_service.delete_object(path)
                    except Exception as s3_error:
                        logger.error(f"Failed to delete S3 file {path} for {document_id}: {s3_error}")
        
        # Soft delete in Firestore
        firestore_svc.soft_delete_document(document_id, deleted_by_uid="system", reason="manual_delete")
        
        # Delete chunks from Postgres
        db.query(DocumentChunk).filter(
            DocumentChunk.tenant_id == DEFAULT_TENANT_ID,
            DocumentChunk.doc_id == document_id
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {"status": "success", "message": f"Document {document_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

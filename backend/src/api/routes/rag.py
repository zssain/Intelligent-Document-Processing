from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.database.base import get_db
from src.database.models import DocumentChunk
from src.processing import process_document, IngestionResult
from src.rag.retriever import Retriever
from src.rag.qa import QualityAssurance
from src.api.models.rag import QueryRequest, QueryResponse, IngestResponse
from src.api.auth import CurrentUser, get_current_user
from src.storage.documents import DocumentStorage
from src.storage.s3_service import S3Service
from config.settings import settings, DEFAULT_TENANT_ID
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize components (only QA is needed at module level)
qa_service = QualityAssurance()

# Initialize S3 service
try:
    s3_service = S3Service()
except Exception as e:
    logger.error(f"Failed to initialize S3 service: {e}")
    s3_service = None

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a document, process with DI, and index for RAG.

    The entire operation (Document row + chunks) is committed atomically:
    either everything succeeds or nothing is persisted.
    """
    ext = os.path.splitext(file.filename or "")[1].lstrip(".").lower()
    if ext not in settings.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '.{ext}'. "
                f"Supported: {', '.join(settings.supported_extensions)}"
            ),
        )

    file_path: str | None = None
    try:
        # 1. Save file locally
        content = await file.read()
        file_path = await DocumentStorage.save_upload(content, file.filename)
        file_size_bytes = os.path.getsize(file_path)

        # 2. Upload source PDF to S3 (optional, non-fatal)
        s3_url = None
        if s3_service:
            try:
                s3_url = s3_service.upload_pdf(file_path, file.filename)
                if s3_url:
                    logger.info("PDF uploaded to S3: %s", s3_url)
            except Exception as s3_err:
                logger.error("S3 upload failed (continuing): %s", s3_err)

        # 3. Run the full pipeline (CU → normalize → chunk → embed → Firestore + DB)
        result: IngestionResult = process_document(
            file_path=file_path,
            filename=file.filename,
            db=db,
            tenant_id=DEFAULT_TENANT_ID,
            s3_service=s3_service,
            s3_url=s3_url,
            file_size_bytes=file_size_bytes,
            source="local",
            source_metadata={},
        )

        # 4. Commit the whole transaction atomically
        db.commit()

        return IngestResponse(
            status="success",
            document_id=result.document_id,
            chunks_count=result.chunks_count,
        )

    except Exception as e:
        db.rollback()
        logger.error("Ingestion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Answers a question using retrieval-augmented generation."""
    logger.info(f"Query request received: question='{request.question}', language='{request.language}', user={current_user.uid}")
    try:
        # 1. Retrieve (with RBAC filtering)
        retriever = Retriever(db, current_user=current_user)
        context = retriever.get_relevant_context(
            request.question,
            entity=request.entity,
            document_type=request.document_type,
            document_ids=request.document_ids
        )
        
        # 2. QA
        result = qa_service.answer_question(request.question, context, language=request.language)
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query/stream")
async def query_rag_stream(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Answers a question using retrieval-augmented generation with streaming."""
    logger.info(f"Streaming query request received: question='{request.question}', language='{request.language}', user={current_user.uid}")
    try:
        # Pass parameters to stream_answer which now handles retrieval internally for speed
        return StreamingResponse(
            qa_service.stream_answer(
                request.question,
                db,
                language=request.language,
                entity=request.entity,
                document_type=request.document_type,
                document_ids=request.document_ids,
                current_user=current_user,
            ),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Streaming Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

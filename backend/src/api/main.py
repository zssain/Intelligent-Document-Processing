"""FastAPI application initialization."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.base import get_db
from src.api.routes import upload, content_understanding, rag, dashboard
from src.api.routes import datalake_s3
from src.api.routes import datalake_sharepoint
from src.api.routes import datalake_gdrive
from config.settings import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(content_understanding.router, prefix="/api/v1/cu", tags=["content-understanding"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(datalake_s3.router, prefix="/api/v1/datalake", tags=["datalake"])
app.include_router(datalake_sharepoint.router, prefix="/api/v1/datalake", tags=["datalake-sharepoint"])
app.include_router(datalake_gdrive.router, prefix="/api/v1/datalake", tags=["datalake-gdrive"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "BlueTide Document RAG API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/api/v1/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint including DB status."""
    db_status = "healthy"
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": db_status
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting BlueTide Document RAG API...")
    
    # Create directories
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.processed_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Ensure IngestionCursor table exists (idempotent create_all)
    from src.database.base import engine, Base
    from src.database.models import IngestionCursor  # noqa: F401 – force registration
    try:
        IngestionCursor.__table__.create(engine, checkfirst=True)
        logger.info("IngestionCursor table ready")
    except Exception as e:
        logger.warning(f"Could not auto-create ingestion_cursors table: {e}")
    
    logger.info("API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down BlueTide Document RAG API...")

"""FastAPI application initialization."""

from fastapi import APIRouter, FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.base import get_db
from src.api.auth import get_current_user, CurrentUser
from src.api.routes import upload, content_understanding, rag, dashboard
from src.api.routes import datalake_s3
from src.api.routes import datalake_sharepoint
from src.api.routes import datalake_gdrive
from src.api.routes import admin as admin_routes
from src.api.routes import documents as documents_routes
from src.api.routes import oauth as oauth_routes
from src.api.routes import jobs as jobs_routes
from src.api.routes import link_connect as link_connect_routes
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

# ── Proxy headers middleware ─────────────────────────────────────
# Behind App Runner / ALB, the app receives plain HTTP but the actual
# client connection is HTTPS.  This middleware reads X-Forwarded-Proto &
# X-Forwarded-For headers so that request.url_for() generates correct
# https:// URLs (critical for OAuth redirect_uri).
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Configure CORS
# When CORS_ORIGINS='*', credentials must be disabled (browser requirement).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=not settings.cors_allow_all and settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# ---------------------------------------------------------------------------
# Authenticated router – all protected sub-routers are mounted here so that
# ``get_current_user`` runs automatically on every request.
# ---------------------------------------------------------------------------
authenticated_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

authenticated_router.include_router(upload.router, tags=["Upload"])
authenticated_router.include_router(content_understanding.router, prefix="/cu", tags=["content-understanding"])
authenticated_router.include_router(rag.router, prefix="/rag", tags=["rag"])
authenticated_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
authenticated_router.include_router(datalake_s3.router, prefix="/datalake", tags=["datalake"])
authenticated_router.include_router(datalake_sharepoint.router, prefix="/datalake", tags=["datalake-sharepoint"])
authenticated_router.include_router(datalake_gdrive.router, prefix="/datalake", tags=["datalake-gdrive"])
authenticated_router.include_router(admin_routes.router, prefix="/admin", tags=["Admin"])
authenticated_router.include_router(documents_routes.router, tags=["Documents"])
authenticated_router.include_router(oauth_routes.router, prefix="/auth", tags=["OAuth"])
authenticated_router.include_router(jobs_routes.router, prefix="/jobs", tags=["Jobs"])
authenticated_router.include_router(link_connect_routes.router, prefix="/sources", tags=["Source Connections"])

app.include_router(authenticated_router)

# OAuth callback routes must be public (Google/Azure redirect here via browser)
app.include_router(oauth_routes.public_router, prefix="/api/v1/auth", tags=["OAuth Callbacks"])


# ---------------------------------------------------------------------------
# User self-service endpoints (auth required, no admin role needed)
# ---------------------------------------------------------------------------
@app.get("/api/v1/users/me/permissions", tags=["Users"])
async def get_my_permissions(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return the current user's full permission set.

    Used by the frontend to know which connectors/actions to show/hide.
    """
    return {
        "uid": current_user.uid,
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "clearance_level": current_user.clearance_level,
        "allowed_category_ids": current_user.allowed_category_ids,
        "allowed_sources": current_user.allowed_sources,
        "source_permissions": current_user.source_permissions,
    }


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------
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
    os.makedirs(settings.raw_dir, exist_ok=True)
    os.makedirs(settings.normalized_dir, exist_ok=True)
    os.makedirs(settings.vector_db_path, exist_ok=True)
    os.makedirs(settings.logs_dir, exist_ok=True)

    logger.info("API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down BlueTide Document RAG API...")

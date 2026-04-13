from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional
from functools import lru_cache
import os

# ── Firebase ─────────────────────────────────────────────────────
DEFAULT_TENANT_ID = "default-tenant"


def _running_on_lambda() -> bool:
    """Detect the AWS Lambda runtime without requiring explicit config."""
    exec_env = os.getenv("AWS_EXECUTION_ENV", "")
    return bool(
        os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("AWS_LAMBDA_RUNTIME_API")
        or exec_env.startswith("AWS_Lambda")
    )


def _runtime_path(path_suffix: str) -> str:
    """Store writable runtime files under /tmp on Lambda."""
    if _running_on_lambda():
        return f"/tmp/{path_suffix.lstrip('/')}"
    return path_suffix


def _parse_cors_origins() -> List[str]:
    """Build CORS origins from CORS_ORIGINS env var (comma-separated)
    merged with the hardcoded local dev origins."""
    defaults = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
    ]
    extra = os.getenv("CORS_ORIGINS", "")
    if extra:
        defaults.extend([o.strip() for o in extra.split(",") if o.strip()])
    return defaults


class Settings(BaseSettings):
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    allowed_extensions: List[str] = [
        "pdf", "docx", "xlsx", "pptx", "html",
        "tiff", "tif", "jpg", "jpeg", "png", "bmp",
    ]
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App metadata ─────────────────────────────
    app_name: str = "BlueTide Document RAG API"
    app_description: str = "AI-powered document processing and analysis system"
    app_version: str = "1.0.0"

    # ── Server ───────────────────────────────────
    port: int = 8000  # App Runner will set PORT env var

    # ── CORS ─────────────────────────────────────
    cors_origins: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _coerce_cors_origins(cls, v):
        """Accept plain string from env-var; the property below splits it."""
        if isinstance(v, list):
            return ",".join(v)
        return v or ""

    @property
    def cors_allow_all(self) -> bool:
        """True when CORS_ORIGINS is set to '*' (allow every origin)."""
        return self.cors_origins.strip() == "*"

    @property
    def cors_origins_list(self) -> List[str]:
        """Return the merged list of allowed origins."""
        # If wildcard, allow all origins
        if self.cors_allow_all:
            return ["*"]
        defaults = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:4173",
        ]
        if self.cors_origins:
            defaults.extend([o.strip() for o in self.cors_origins.split(",") if o.strip()])
        return defaults
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # ── Azure Document Intelligence 4.0 ──────────
    azure_doc_endpoint: str = ""
    azure_doc_key: str = ""

    # ── Extraction backend selection ──────────────
    # "docling" = Docling + Gemini (primary, local + LLM)
    # "azure"   = Azure Document Intelligence 4.0 (fallback / legacy)
    extraction_backend: str = "docling"

    # ── Google Gemini (used by Docling backend) ───
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Azure AI Content Understanding ────────────
    azure_cu_endpoint: str = ""
    azure_cu_key: str = ""
    azure_cu_analyzer_id: str = ""

    # ── Supported file types for ingestion ────────
    supported_extensions: List[str] = [
        "pdf", "docx", "xlsx", "pptx", "html",
        "tiff", "tif", "jpg", "jpeg", "png", "bmp",
    ]

    # ── GPT-4o enhancement (feature flag) ─────────
    enable_gpt4o_enhancement: bool = False

    # ── Ingestion concurrency caps ────────────────
    max_concurrent_ingest: int = 5           # global per-instance
    max_concurrent_ingest_per_tenant: int = 3

    # ── OAuth / Account Linking ───────────────────
    token_encryption_key: str = ""  # Fernet key for encrypting OAuth tokens
    gdrive_oauth_client_id: str = ""
    gdrive_oauth_client_secret: str = ""
    sharepoint_oauth_client_id: str = ""
    sharepoint_oauth_client_secret: str = ""
    # Legacy reverse-proxy mode where the frontend serves /api/* and forwards
    # callbacks to the backend (kept for the archived App Runner path).
    frontend_url: str = ""
    # Preferred production callback base for direct backend hosting such as
    # Lambda Function URLs, API Gateway, or a backend custom domain.
    backend_public_url: str = ""

    # ── OpenAI ───────────────────────────────────
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # ── Vector DB ────────────────────────────────
    vector_db_provider: str = "chroma"
    vector_db_path: str = _runtime_path("data/vector_store")

    # ── Database ─────────────────────────────────
    neon_connection_string: str

    # ── Storage ──────────────────────────────────
    upload_dir: str = _runtime_path("data/raw")
    processed_dir: str = _runtime_path("data/processed")
    raw_dir: str = _runtime_path("data/raw_cu")
    normalized_dir: str = _runtime_path("data/normalized")
    logs_dir: str = _runtime_path("logs")
    debug: bool = True

    # ── AWS S3 ───────────────────────────────────
    # Keys are optional: when running on EC2/ECS/Lambda, IAM role auth is used
    # instead.  Set them explicitly only for local development.
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket_name: str = "bluetide-docs"
    aws_region: str = "eu-north-1"
    s3_pdf_prefix: str = "documents/"

    # ── S3 Datalake ──────────────────────────────
    # Prefix under which datalake source PDFs are stored (e.g. datalake/Invoices/).
    s3_datalake_prefix: str = "datalake/"
    # Safety guard: maximum number of PDFs to process in a single /sync call.
    s3_sync_max_files: int = 500
    # Optional queue used by Lambda/API deployments to dispatch ingestion jobs
    # to a separate worker function.
    job_queue_url: str = ""

    # ── API Key (simple dev auth) ────────────────
    # Set to a non-empty string to require X-API-Key header on protected endpoints.
    api_key: str = ""

    # ── SharePoint / Microsoft Graph (app-only auth) ──────────────
    # Register an Azure AD App Registration with Application permissions:
    #   Sites.Read.All, Files.Read.All  – then grant Admin Consent.
    # Token endpoint: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
    # Scope: https://graph.microsoft.com/.default
    sharepoint_tenant_id: str = ""
    sharepoint_client_id: str = ""
    sharepoint_client_secret: str = ""
    # Provide *either* site_id directly, *or* site_url to resolve it.
    sharepoint_site_id: str = ""
    sharepoint_site_url: str = ""   # e.g. "yourorg.sharepoint.com:/sites/MySite"
    # Drive ID – leave empty to auto-resolve the default document library.
    sharepoint_drive_id: str = ""
    # Folder path inside the document library (no leading "/").
    sharepoint_folder_path: str = "Shared Documents/datalake"
    # Safety guard: max items per sync call.
    sharepoint_sync_max_files: int = 500

    # ── Google Drive ─────────────────────────────────────────────────
    # Two auth modes are supported:
    #   1. OAuth2 refresh token – set client_id + client_secret + refresh_token.
    #      Quickest for personal Drive / testing.
    #   2. Service Account – set gdrive_use_service_account = true and provide
    #      the JSON key via gdrive_service_account_json (path or raw JSON string).
    #      For Google Workspace with domain-wide delegation.
    # Required scope: https://www.googleapis.com/auth/drive.readonly
    gdrive_client_id: str = ""
    gdrive_client_secret: str = ""
    gdrive_refresh_token: str = ""
    gdrive_folder_id: str = ""          # root folder to list / sync
    gdrive_use_service_account: bool = False
    gdrive_service_account_json: str = ""  # file path OR raw JSON via env var
    gdrive_delegated_user: str = ""     # impersonated user (Workspace SA only)
    # Safety guard: max PDFs per sync call.
    gdrive_sync_max_files: int = 500

    # ── Firebase ─────────────────────────────────
    firebase_service_account_key_path: str = (
        "/tmp/firebase-sa.json" if _running_on_lambda() else ""
    )

    # ── DB Pooling ───────────────────────────────
    # Keep the defaults small on Lambda to avoid opening too many Neon
    # connections under concurrent cold starts.
    db_pool_size: int = 1 if _running_on_lambda() else 5
    db_max_overflow: int = 2 if _running_on_lambda() else 10


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

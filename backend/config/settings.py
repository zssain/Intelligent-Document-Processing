from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
import os


class Settings(BaseSettings):
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    allowed_extensions: List[str] = ["pdf", "png", "jpg", "jpeg"]
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

    # ── CORS ─────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # ── Azure OCR ────────────────────────────────
    azure_doc_endpoint: str
    azure_doc_key: str

    # ── Azure Content Understanding ──────────────
    azure_cu_endpoint: str
    azure_cu_key: str
    azure_cu_analyzer_id: str

    # ── OpenAI ───────────────────────────────────
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # ── Vector DB ────────────────────────────────
    vector_db_provider: str = "chroma"
    vector_db_path: str = "data/vector_store"

    # ── Database ─────────────────────────────────
    neon_connection_string: str

    # ── Storage ──────────────────────────────────
    upload_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    raw_dir: str = "data/raw_cu"
    normalized_dir: str = "data/normalized"
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""Link-based source connection endpoints.

Flow
----
1. ``POST /sources/connect-link``
       User pastes a Google Drive or SharePoint folder URL.
       Backend parses it, verifies access, saves the connection in
       Firestore, and returns the list of supported files.

2. ``GET  /sources/connections``
       List saved source connections for the current tenant.

3. ``GET  /sources/{connection_id}/files``
       Re-fetch (refresh) the file list for a saved connection.

4. ``DELETE /sources/{connection_id}``
       Remove a saved connection.

Firestore path:  tenants/{tenant_id}/source_connections/{connection_id}
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from config.settings import settings
from src.api.auth import CurrentUser, get_current_user
from src.connectors.link_parser import parse_drive_link, LinkProvider
from src.utils.firebase import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Pydantic models ───────────────────────────────────────────────────────


class ConnectLinkRequest(BaseModel):
    url: str = Field(..., description="Google Drive or SharePoint folder URL")
    label: Optional[str] = Field(
        None, description="Optional display name for this connection"
    )


class FileInfo(BaseModel):
    file_id: str
    name: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    modified_at: Optional[str] = None
    web_url: Optional[str] = None


class ConnectionInfo(BaseModel):
    connection_id: str
    provider: str
    label: str
    folder_id: Optional[str] = None
    site_hostname: Optional[str] = None
    site_path: Optional[str] = None
    item_path: Optional[str] = None
    original_url: str
    status: str  # "connected" | "error"
    error_message: Optional[str] = None
    file_count: int = 0
    connected_at: str


class ConnectLinkResponse(BaseModel):
    connection: ConnectionInfo
    files: List[FileInfo]


# ── Helpers ───────────────────────────────────────────────────────────────


def _conn_ref(db, tenant_id: str, connection_id: str):
    """Firestore document reference for a source connection."""
    return (
        db.collection("tenants")
        .document(tenant_id)
        .collection("source_connections")
        .document(connection_id)
    )


def _get_user_tokens(db, tenant_id: str, user_id: str, provider: str) -> Optional[Dict]:
    """Load decrypted OAuth tokens for *provider* if the user has linked their account."""
    try:
        from src.api.routes.oauth import _decrypt

        doc_ref = (
            db.collection("tenants")
            .document(tenant_id)
            .collection("user_connections")
            .document(user_id)
        )
        doc = doc_ref.get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        prov_data = data.get(provider)
        if not prov_data or prov_data.get("status") != "connected":
            return None

        return {
            "access_token": _decrypt(prov_data["encrypted_access_token"]),
            "refresh_token": _decrypt(prov_data["encrypted_refresh_token"]),
        }
    except Exception as exc:
        logger.warning("Could not load user tokens for %s: %s", provider, exc)
        return None


def _build_gdrive_client(user_tokens: Optional[Dict] = None):
    """Build a GoogleDriveClient, optionally using per-user OAuth tokens."""
    from src.connectors.google_drive import GoogleDriveClient, GDriveAuthError, _build_credentials
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from googleapiclient.discovery import build as build_service

    if user_tokens and user_tokens.get("access_token"):
        creds = OAuthCredentials(
            token=user_tokens["access_token"],
            refresh_token=user_tokens.get("refresh_token"),
            client_id=settings.gdrive_oauth_client_id or settings.gdrive_client_id,
            client_secret=settings.gdrive_oauth_client_secret or settings.gdrive_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        client = GoogleDriveClient.__new__(GoogleDriveClient)
        client._service = build_service("drive", "v3", credentials=creds)
        return client

    # Fall back to env-configured credentials
    try:
        return GoogleDriveClient()
    except GDriveAuthError as exc:
        logger.error("Google Drive credentials not configured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "GDRIVE_NOT_CONFIGURED",
                "message": (
                    "Google Drive is not configured on the server. "
                    "Please connect your Google account first via 'Connect Account', "
                    "or ask your admin to set up service-account credentials "
                    "(GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN)."
                ),
            },
        )


def _build_graph_client_for_site(
    site_hostname: str,
    site_path: str,
) -> "GraphClient":
    """Build a GraphClient and resolve the site → drive ID for the link."""
    from src.connectors.sharepoint_graph import GraphClient

    client = GraphClient()

    # Resolve site from the link URL instead of env settings
    site_url = f"{site_hostname}:{site_path}"
    site_id = client.resolve_site_id(site_url)
    drive_id = client.resolve_drive_id(site_id)

    return client, site_id, drive_id


def _list_gdrive_files(folder_id: str, user_tokens: Optional[Dict] = None) -> List[FileInfo]:
    """List files in a Google Drive folder, filtered by supported extensions."""
    client = _build_gdrive_client(user_tokens)
    try:
        raw = client.list_folder_files(
            folder_id,
            limit=500,
            supported_extensions=settings.supported_extensions,
        )
    except Exception as exc:
        logger.error("Cannot access Google Drive folder %s: %s", folder_id, exc)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ACCESS_DENIED",
                "message": (
                    f"Cannot access this Google Drive folder. "
                    f"Make sure it is shared with the service account or "
                    f"your connected Google account. Details: {exc}"
                ),
            },
        )

    files: List[FileInfo] = []
    for f in raw:
        files.append(
            FileInfo(
                file_id=f["id"],
                name=f.get("name", ""),
                mime_type=f.get("mimeType"),
                size=int(f.get("size", 0)) if f.get("size") else None,
                modified_at=f.get("modifiedTime"),
                web_url=f.get("webViewLink"),
            )
        )
    return files


def _list_sharepoint_files(
    site_hostname: str,
    site_path: str,
    item_path: Optional[str] = None,
) -> List[FileInfo]:
    """List files in a SharePoint document library folder."""
    try:
        client, site_id, drive_id = _build_graph_client_for_site(
            site_hostname, site_path
        )

        # For connect-via-link, use item_path from the URL (or None for root).
        # Don't fall back to settings.sharepoint_folder_path — that's for
        # env-var-based SharePoint sync and may not exist on this site.
        # Recursively scan subfolders to find all files.
        folder_path = item_path  # None → drive root
        raw = client.list_all_files_recursive(
            drive_id, folder_path, max_files=500
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Cannot access SharePoint folder: %s", exc)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ACCESS_DENIED",
                "message": (
                    f"Cannot access this SharePoint folder. "
                    f"Make sure the app has Sites.Read.All permission. "
                    f"Details: {exc}"
                ),
            },
        )

    supported_set = {ext.lower() for ext in settings.supported_extensions}
    files: List[FileInfo] = []
    for item in raw:
        name = item.get("name", "")
        ext = os.path.splitext(name)[1].lstrip(".").lower()
        if ext not in supported_set:
            continue
        files.append(
            FileInfo(
                file_id=item["id"],
                name=name,
                mime_type=item.get("file", {}).get("mimeType") if isinstance(item.get("file"), dict) else None,
                size=item.get("size"),
                modified_at=item.get("lastModifiedDateTime"),
                web_url=item.get("webUrl"),
            )
        )
    return files


def _auto_label(parsed) -> str:
    """Generate a display label from a parsed link."""
    if parsed.provider == LinkProvider.GDRIVE:
        fid = parsed.folder_id or ""
        return f"Google Drive ({fid[:12]}…)" if len(fid) > 12 else f"Google Drive ({fid})"
    site_name = (parsed.site_path or "").replace("/sites/", "")
    folder = (parsed.item_path or "Root").rsplit("/", 1)[-1]
    return f"{site_name} / {folder}" if site_name else f"SharePoint / {folder}"


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/connect-link", response_model=ConnectLinkResponse)
async def connect_via_link(
    body: ConnectLinkRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Parse a folder URL, verify access, save connection, return file list."""
    db = get_firestore_client()
    tenant_id = user.tenant_id
    user_id = user.uid

    # 1. Parse
    parsed = parse_drive_link(body.url)

    # 2. Resolve user OAuth tokens if available
    provider_key = "gdrive" if parsed.provider == LinkProvider.GDRIVE else "sharepoint"
    user_tokens = _get_user_tokens(db, tenant_id, user_id, provider_key)

    # 3. Verify access + list files
    if parsed.provider == LinkProvider.GDRIVE:
        files = _list_gdrive_files(parsed.folder_id, user_tokens)
    else:
        files = _list_sharepoint_files(
            parsed.site_hostname, parsed.site_path, parsed.item_path
        )

    # 4. Persist connection in Firestore
    connection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    label = body.label or _auto_label(parsed)

    conn_data = {
        "connection_id": connection_id,
        "provider": parsed.provider.value,
        "label": label,
        "folder_id": parsed.folder_id,
        "site_hostname": parsed.site_hostname,
        "site_path": parsed.site_path,
        "item_path": parsed.item_path,
        "original_url": parsed.original_url,
        "status": "connected",
        "error_message": None,
        "file_count": len(files),
        "connected_at": now,
        "created_by": user_id,
        "tenant_id": tenant_id,
    }
    _conn_ref(db, tenant_id, connection_id).set(conn_data)

    info = ConnectionInfo(
        connection_id=connection_id,
        provider=conn_data["provider"],
        label=label,
        folder_id=conn_data["folder_id"],
        site_hostname=conn_data["site_hostname"],
        site_path=conn_data["site_path"],
        item_path=conn_data["item_path"],
        original_url=conn_data["original_url"],
        status="connected",
        file_count=len(files),
        connected_at=now,
    )

    logger.info(
        "Source connection %s created (%s, %d files)",
        connection_id,
        parsed.provider.value,
        len(files),
    )
    return ConnectLinkResponse(connection=info, files=files)


@router.get("/connections", response_model=List[ConnectionInfo])
async def list_connections(
    provider: Optional[str] = Query(None, description="Filter: gdrive | sharepoint"),
    user: CurrentUser = Depends(get_current_user),
):
    """List all saved source connections for the current tenant."""
    try:
        db = get_firestore_client()
        coll = (
            db.collection("tenants")
            .document(user.tenant_id)
            .collection("source_connections")
        )

        query = coll
        if provider:
            query = query.where("provider", "==", provider)

        results: List[ConnectionInfo] = []
        for doc in query.stream():
            d = doc.to_dict()
            results.append(
                ConnectionInfo(
                    connection_id=d.get("connection_id", doc.id),
                    provider=d.get("provider", ""),
                    label=d.get("label", ""),
                    folder_id=d.get("folder_id"),
                    site_hostname=d.get("site_hostname"),
                    site_path=d.get("site_path"),
                    item_path=d.get("item_path"),
                    original_url=d.get("original_url", ""),
                    status=d.get("status", "connected"),
                    error_message=d.get("error_message"),
                    file_count=d.get("file_count", 0),
                    connected_at=d.get("connected_at", ""),
                )
            )
        return results
    except Exception as exc:
        logger.warning("Could not list source connections: %s", exc)
        return []


@router.get("/{connection_id}/files", response_model=List[FileInfo])
async def list_connection_files(
    connection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Re-fetch file list for a saved connection."""
    db = get_firestore_client()
    tenant_id = user.tenant_id

    doc = _conn_ref(db, tenant_id, connection_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Connection not found")

    conn = doc.to_dict()

    # Verify same tenant
    if conn.get("tenant_id") and conn["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="Connection not found")

    user_tokens = _get_user_tokens(db, tenant_id, user.uid, conn["provider"])

    if conn["provider"] == LinkProvider.GDRIVE.value:
        files = _list_gdrive_files(conn["folder_id"], user_tokens)
    else:
        files = _list_sharepoint_files(
            conn["site_hostname"], conn["site_path"], conn.get("item_path")
        )

    # Update cached file count
    _conn_ref(db, tenant_id, connection_id).update({"file_count": len(files)})

    return files


@router.delete("/{connection_id}")
async def disconnect_source(
    connection_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Remove a saved source connection."""
    db = get_firestore_client()
    tenant_id = user.tenant_id

    ref = _conn_ref(db, tenant_id, connection_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Connection not found")

    ref.delete()
    logger.info("Source connection %s deleted by %s", connection_id, user.uid)
    return {"status": "disconnected", "connection_id": connection_id}

"""Google Drive connector using the official Python client library.

Auth modes
----------
1. **OAuth2 refresh token** – quickest for personal Drive / testing.
   Set ``GDRIVE_CLIENT_ID``, ``GDRIVE_CLIENT_SECRET``, ``GDRIVE_REFRESH_TOKEN``.

2. **Service Account** – for Google Workspace with domain-wide delegation.
   Set ``GDRIVE_USE_SERVICE_ACCOUNT=true`` and ``GDRIVE_SERVICE_ACCOUNT_JSON``
   (path to a JSON key file, or the raw JSON string itself).
   Optionally set ``GDRIVE_DELEGATED_USER`` to impersonate a user.

Required OAuth scope (either mode):
    https://www.googleapis.com/auth/drive.readonly

Changes API
-----------
The ``changes_query`` method wraps the Drive Changes API so that subsequent
syncs only receive items modified since the last call.  The ``pageToken`` is
stored externally (in the ``ingestion_cursors`` DB table).
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2 import service_account as sa_module
from googleapiclient.discovery import build as build_service
from googleapiclient.http import MediaIoBaseDownload

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Fields we want back from the Files API
_FILE_FIELDS = (
    "id, name, mimeType, modifiedTime, size, md5Checksum, "
    "version, webViewLink, parents, trashed"
)
_LIST_FIELDS = f"nextPageToken, files({_FILE_FIELDS})"


class GDriveAuthError(Exception):
    """Raised when credential building fails."""


class GDriveAPIError(Exception):
    """Raised on non-recoverable Drive API errors."""


# ---------------------------------------------------------------------------
# Credential builders
# ---------------------------------------------------------------------------

def _build_oauth_creds() -> OAuthCredentials:
    """Build OAuth2 credentials from client_id / client_secret / refresh_token."""
    if not all([
        settings.gdrive_client_id,
        settings.gdrive_client_secret,
        settings.gdrive_refresh_token,
    ]):
        raise GDriveAuthError(
            "OAuth2 mode requires GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, "
            "and GDRIVE_REFRESH_TOKEN."
        )
    creds = OAuthCredentials(
        token=None,
        refresh_token=settings.gdrive_refresh_token,
        client_id=settings.gdrive_client_id,
        client_secret=settings.gdrive_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(GoogleAuthRequest())
    logger.info("Google Drive OAuth2 token acquired")
    return creds


def _build_service_account_creds() -> sa_module.Credentials:
    """Build Service Account credentials (with optional delegation)."""
    sa_json = settings.gdrive_service_account_json
    if not sa_json:
        raise GDriveAuthError(
            "Service-account mode requires GDRIVE_SERVICE_ACCOUNT_JSON "
            "(file path or raw JSON)."
        )

    # Determine if it's a file path or raw JSON
    if os.path.isfile(sa_json):
        creds = sa_module.Credentials.from_service_account_file(
            sa_json, scopes=SCOPES
        )
    else:
        info = json.loads(sa_json)
        creds = sa_module.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )

    if settings.gdrive_delegated_user:
        creds = creds.with_subject(settings.gdrive_delegated_user)

    logger.info("Google Drive Service Account credentials loaded")
    return creds


def _build_credentials():
    """Return appropriate credentials based on settings."""
    if settings.gdrive_use_service_account:
        return _build_service_account_creds()
    return _build_oauth_creds()


# ---------------------------------------------------------------------------
# Public client class
# ---------------------------------------------------------------------------

class GoogleDriveClient:
    """High-level wrapper around the Google Drive v3 API."""

    def __init__(self):
        try:
            creds = _build_credentials()
            self._service = build_service("drive", "v3", credentials=creds)
            logger.info("GoogleDriveClient initialised")
        except Exception as exc:
            logger.error("Failed to build Google Drive client: %s", exc)
            raise

    # ── List files in folder ──────────────────────────────────────────────

    def list_folder_files(
        self,
        folder_id: str,
        *,
        limit: int = 100,
        supported_extensions: list[str] | None = None,
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """List files inside *folder_id*, optionally recursing into subfolders.

        When *supported_extensions* is provided (e.g. ``["pdf", "docx", …]``)
        only files whose name ends with one of those extensions are returned.
        Otherwise all non-trashed files are returned.

        When *recursive* is ``True`` (default), subfolders are traversed
        depth-first so that files nested at any depth are included.
        """
        items: List[Dict[str, Any]] = []
        folders_to_scan = [folder_id]

        while folders_to_scan and len(items) < limit:
            current_folder = folders_to_scan.pop(0)
            q = (
                f"'{current_folder}' in parents "
                "and trashed=false"
            )
            page_token: Optional[str] = None

            while len(items) < limit:
                page_size = min(100, limit - len(items))
                request = self._service.files().list(
                    q=q,
                    fields=_LIST_FIELDS,
                    pageSize=page_size,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                resp = request.execute()
                for f in resp.get("files", []):
                    mime = f.get("mimeType", "")
                    # Queue subfolders for recursive scanning
                    if mime == "application/vnd.google-apps.folder":
                        if recursive:
                            folders_to_scan.append(f["id"])
                            logger.info(
                                "Queued subfolder '%s' (%s) for recursive scan",
                                f.get("name", ""), f["id"],
                            )
                        continue

                    if supported_extensions:
                        ext = os.path.splitext(f.get("name", ""))[1].lstrip(".").lower()
                        if ext not in supported_extensions:
                            continue
                    items.append(f)
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break

        logger.info(
            "list_folder_files('%s', recursive=%s) returned %d items",
            folder_id, recursive, len(items),
        )
        return items[:limit]

    # Keep backward-compat alias
    list_folder_pdfs = list_folder_files

    # ── Changes (delta) API ───────────────────────────────────────────────

    def get_start_page_token(self) -> str:
        """Get the initial ``startPageToken`` for the Changes API."""
        resp = (
            self._service.changes()
            .getStartPageToken(supportsAllDrives=True)
            .execute()
        )
        token = resp["startPageToken"]
        logger.info("Drive start page token: %s", token)
        return token

    def changes_query(
        self,
        folder_id: str,
        page_token: Optional[str] = None,
        *,
        max_items: int = 1000,
        supported_extensions: list[str] | None = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Fetch changed files since *page_token*.

        If *page_token* is ``None`` a fresh ``startPageToken`` is obtained
        first (first-run scenario – returns no items, only the cursor).

        Returns
        -------
        items : list[dict]
            Changed file metadata dicts (only PDFs in *folder_id*).
        new_page_token : str
            Token for the next invocation.
        """
        if page_token is None:
            # First run – just grab the cursor, no items
            return [], self.get_start_page_token()

        items: List[Dict[str, Any]] = []
        current_token = page_token

        while len(items) < max_items:
            resp = (
                self._service.changes()
                .list(
                    pageToken=current_token,
                    fields=(
                        "nextPageToken, newStartPageToken, "
                        f"changes(fileId, removed, file({_FILE_FIELDS}))"
                    ),
                    pageSize=min(100, max_items - len(items)),
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            for change in resp.get("changes", []):
                if change.get("removed"):
                    continue
                file_meta = change.get("file")
                if not file_meta:
                    continue
                # Filter by supported extensions and target folder
                if file_meta.get("trashed"):
                    continue
                if supported_extensions:
                    ext = os.path.splitext(file_meta.get("name", ""))[1].lstrip(".").lower()
                    if ext not in supported_extensions:
                        continue
                parents = file_meta.get("parents") or []
                if folder_id not in parents:
                    continue
                items.append(file_meta)

            if "newStartPageToken" in resp:
                # Reached the end of the changes stream
                current_token = resp["newStartPageToken"]
                break
            current_token = resp["nextPageToken"]

        logger.info(
            "changes_query('%s') returned %d changed PDFs, new token=%s",
            folder_id, len(items), current_token[:20] + "…" if len(current_token) > 20 else current_token,
        )
        return items[:max_items], current_token

    # ── Download ──────────────────────────────────────────────────────────

    def download_file(self, file_id: str, filename: str = "") -> str:
        """Download a Drive file to a local temp file and return the path.

        Caller is responsible for deleting the temp file.
        """
        suffix = os.path.splitext(filename)[1] if filename else ".bin"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix or ".bin")
        os.close(fd)
        try:
            request = self._service.files().get_media(
                fileId=file_id, supportsAllDrives=True
            )
            with open(tmp_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
                done = False
                while not done:
                    _status, done = downloader.next_chunk()
            logger.info("Downloaded Drive file %s -> %s", file_id, tmp_path)
            return tmp_path
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


__all__ = ["GoogleDriveClient", "GDriveAuthError", "GDriveAPIError"]

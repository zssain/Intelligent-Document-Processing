"""Microsoft Graph client for SharePoint document access (app-only auth).

Token endpoint
--------------
POST https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
    grant_type=client_credentials
    client_id=...
    client_secret=...
    scope=https://graph.microsoft.com/.default

Required Azure AD **Application** permissions (with Admin Consent):
    - Sites.Read.All
    - Files.Read.All

Graph API docs used
-------------------
* List children:  GET /drives/{driveId}/root:/{path}:/children
* Delta query:    GET /drives/{driveId}/root:/{path}:/delta
* Download:       GET /drives/{driveId}/items/{itemId}/content
* Resolve site:   GET /sites/{host}:/{path}
* Resolve drive:  GET /sites/{siteId}/drive
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

# Retry-able HTTP status codes (429 = throttled, 503 = service unavailable)
_RETRYABLE = {429, 500, 502, 503, 504}
_MAX_RETRIES = 4
_BACKOFF_BASE = 2  # seconds


class GraphAuthError(Exception):
    """Raised when token acquisition fails."""


class GraphAPIError(Exception):
    """Raised on non-retryable Graph API errors."""


class GraphClient:
    """Thin Microsoft Graph REST client with app-only (client_credentials) auth.

    Features:
    - Token caching with automatic refresh (tokens last ~3600 s).
    - Automatic retry with exponential back-off on 429 / 5xx.
    - Pagination via ``@odata.nextLink``.
    """

    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.tenant_id = tenant_id or settings.sharepoint_tenant_id
        self.client_id = client_id or settings.sharepoint_client_id
        self.client_secret = client_secret or settings.sharepoint_client_secret

        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise GraphAuthError(
                "SharePoint connector requires SHAREPOINT_TENANT_ID, "
                "SHAREPOINT_CLIENT_ID, and SHAREPOINT_CLIENT_SECRET."
            )

        self._token: str | None = None
        self._token_expiry: datetime = datetime.now(timezone.utc)
        self._http = httpx.Client(timeout=60, follow_redirects=True)
        logger.info("GraphClient initialised for tenant %s", self.tenant_id)

    # ── Token management ──────────────────────────────────────────────────
    def _acquire_token(self) -> str:
        """Request a new app-only token from Azure AD."""
        url = TOKEN_URL_TPL.format(tenant=self.tenant_id)
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        resp = self._http.post(url, data=data)
        if resp.status_code != 200:
            raise GraphAuthError(
                f"Token request failed ({resp.status_code}): {resp.text}"
            )
        body = resp.json()
        self._token = body["access_token"]
        expires_in = int(body.get("expires_in", 3600))
        # Refresh 5 min before expiry to avoid clock-skew issues
        self._token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in - 300
        )
        logger.debug("Graph token acquired, expires at %s", self._token_expiry)
        return self._token

    def _get_token(self) -> str:
        if self._token is None or datetime.now(timezone.utc) >= self._token_expiry:
            return self._acquire_token()
        return self._token

    # ── Generic HTTP with retry ───────────────────────────────────────────
    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Issue an authenticated Graph API request with retry + back-off."""
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            headers = {"Authorization": f"Bearer {self._get_token()}"}
            try:
                resp = self._http.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                )
                if resp.status_code < 300:
                    return resp
                if resp.status_code in _RETRYABLE:
                    retry_after = int(resp.headers.get("Retry-After", _BACKOFF_BASE ** attempt))
                    logger.warning(
                        "Graph %s %s returned %s – retrying in %ds (attempt %d/%d)",
                        method, url, resp.status_code, retry_after, attempt, _MAX_RETRIES,
                    )
                    time.sleep(retry_after)
                    last_exc = GraphAPIError(f"{resp.status_code}: {resp.text[:300]}")
                    continue
                # Non-retryable error
                raise GraphAPIError(
                    f"Graph {method} {url} failed ({resp.status_code}): {resp.text[:500]}"
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = _BACKOFF_BASE ** attempt
                logger.warning(
                    "Graph HTTP error on %s %s: %s – retrying in %ds",
                    method, url, exc, wait,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"Graph request failed after {_MAX_RETRIES} attempts"
        ) from last_exc

    def _get_json(self, url: str, *, params: dict | None = None) -> dict:
        return self.request("GET", url, params=params).json()

    # ── Resolve helpers ───────────────────────────────────────────────────
    def resolve_site_id(self, site_url: str | None = None) -> str:
        """Resolve a SharePoint site URL to its Graph site ID.

        ``site_url`` should look like ``yourorg.sharepoint.com:/sites/MySite``
        (hostname + server-relative path).
        """
        url = site_url or settings.sharepoint_site_url
        if not url:
            raise GraphAPIError(
                "Cannot resolve site_id: neither SHAREPOINT_SITE_ID nor "
                "SHAREPOINT_SITE_URL is set."
            )
        # Strip protocol if present
        url = url.removeprefix("https://").removeprefix("http://")
        # Graph expects /sites/{host}:/{path}
        # E.g. /sites/contoso.sharepoint.com:/sites/MySite
        endpoint = f"{GRAPH_BASE}/sites/{url}"
        data = self._get_json(endpoint)
        site_id = data["id"]
        logger.info("Resolved site URL '%s' -> site ID '%s'", url, site_id)
        return site_id

    def resolve_drive_id(self, site_id: str) -> str:
        """Return the default document library drive ID for the given site."""
        endpoint = f"{GRAPH_BASE}/sites/{site_id}/drive"
        data = self._get_json(endpoint)
        drive_id = data["id"]
        logger.info("Resolved default drive for site %s -> %s", site_id, drive_id)
        return drive_id

    def get_site_and_drive(self) -> Tuple[str, str]:
        """Return (site_id, drive_id) from settings, resolving as needed."""
        site_id = settings.sharepoint_site_id
        if not site_id:
            site_id = self.resolve_site_id()

        drive_id = settings.sharepoint_drive_id
        if not drive_id:
            drive_id = self.resolve_drive_id(site_id)

        return site_id, drive_id

    # ── List folder children (full scan) ──────────────────────────────────
    def list_folder_children(
        self,
        drive_id: str,
        folder_path: str,
        *,
        max_items: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Return all items (files + sub-folders) under *folder_path*.

        Handles ``@odata.nextLink`` pagination automatically.
        """
        # Encode the path in the URL: /drives/{id}/root:/{path}:/children
        encoded = folder_path.replace(" ", "%20")
        url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{encoded}:/children"
        items: List[Dict[str, Any]] = []

        while url and len(items) < max_items:
            data = self._get_json(url)
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

        logger.info(
            "list_folder_children('%s') returned %d items", folder_path, len(items)
        )
        return items[:max_items]

    # ── Delta query (incremental) ─────────────────────────────────────────
    def delta_query(
        self,
        drive_id: str,
        folder_path: str,
        delta_link: str | None = None,
        *,
        max_items: int = 2000,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        """Run a delta query for *folder_path* and return (items, new_delta_link).

        If *delta_link* is provided the query resumes from that cursor.
        Otherwise a fresh delta enumeration is started.

        Returns
        -------
        items : list[dict]
            Changed / new items since the last delta call.
        new_delta_link : str | None
            Opaque link to pass on the next invocation.
        """
        if delta_link:
            url = delta_link
        else:
            encoded = folder_path.replace(" ", "%20")
            url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{encoded}:/delta"

        items: List[Dict[str, Any]] = []
        new_delta_link: str | None = None

        while url and len(items) < max_items:
            data = self._get_json(url)
            items.extend(data.get("value", []))
            # nextLink = more pages in this delta batch
            # deltaLink = cursor for the *next* call (present on last page)
            url = data.get("@odata.nextLink")
            if "@odata.deltaLink" in data:
                new_delta_link = data["@odata.deltaLink"]

        logger.info(
            "delta_query('%s') returned %d items, new deltaLink=%s",
            folder_path, len(items), bool(new_delta_link),
        )
        return items[:max_items], new_delta_link

    # ── Download ──────────────────────────────────────────────────────────
    def download_file(self, drive_id: str, item_id: str) -> str:
        """Download a drive item to a local temp file and return the path.

        Caller is responsible for deleting the temp file.
        """
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"
        headers = {"Authorization": f"Bearer {self._get_token()}"}

        fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            with self._http.stream("GET", url, headers=headers, follow_redirects=True) as resp:
                if resp.status_code >= 300:
                    raise GraphAPIError(
                        f"Download {item_id} failed ({resp.status_code})"
                    )
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                        f.write(chunk)
            logger.info("Downloaded item %s -> %s", item_id, tmp_path)
            return tmp_path
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    # ── Cleanup ───────────────────────────────────────────────────────────
    def close(self) -> None:
        self._http.close()

    def __del__(self) -> None:
        try:
            self._http.close()
        except Exception:
            pass


__all__ = ["GraphClient", "GraphAuthError", "GraphAPIError"]

"""Parse user-provided Google Drive / SharePoint URLs into actionable references.

Supported formats
-----------------
Google Drive:
    https://drive.google.com/drive/folders/<FOLDER_ID>
    https://drive.google.com/drive/folders/<FOLDER_ID>?usp=sharing
    https://drive.google.com/drive/u/0/folders/<FOLDER_ID>

SharePoint:
    # Direct doc-library links
    https://<tenant>.sharepoint.com/sites/<SiteName>/Shared Documents/<FolderPath>
    https://<tenant>.sharepoint.com/sites/<SiteName>/Documents/Forms/AllItems.aspx?...&id=...
    # Sharing links with /r/ or /s/ prefix  (/:f:/r/  /:f:/s/  /:w:/s/  etc.)
    https://<tenant>.sharepoint.com/:f:/r/sites/<SiteName>/Shared Documents/<FolderPath>
    https://<tenant>.sharepoint.com/:f:/s/<SiteName>/<encoded_id>?e=...
    https://<tenant>.sharepoint.com/:f:/s/sites/<SiteName>/<encoded_id>?e=...
    # Short sharing links with /s/ (alias for /sites/)
    https://<tenant>.sharepoint.com/:f:/s/<SiteName>/<id>
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from urllib.parse import unquote

from fastapi import HTTPException


class LinkProvider(str, Enum):
    GDRIVE = "gdrive"
    SHAREPOINT = "sharepoint"


@dataclass
class ParsedLink:
    provider: LinkProvider
    original_url: str = ""
    # Google Drive
    folder_id: Optional[str] = None
    # SharePoint
    site_hostname: Optional[str] = None
    site_path: Optional[str] = None        # e.g. /sites/MySite
    item_path: Optional[str] = None        # folder path within drive


# ── Google Drive patterns ─────────────────────────────────────────────────
_GDRIVE_FOLDER_RE = re.compile(
    r"https?://drive\.google\.com/drive(?:/u/\d+)?/folders/([a-zA-Z0-9_-]+)"
)

# ── SharePoint patterns ──────────────────────────────────────────────────

# Pattern 1: Full /sites/<SiteName> style URLs (with optional sharing prefixes)
_SP_SITE_RE = re.compile(
    r"https?://([a-zA-Z0-9-]+\.sharepoint\.com)"   # hostname
    r"(?:/[a-z:]+)*"                                # optional sharing prefixes: /u:/r/, /:f:/r/, /:f:/s/ …
    r"(/sites/[^/?#]+)"                             # /sites/<SiteName>
)

# Pattern 2: Short sharing links — /:f:/s/<SiteName>/<encoded_id>
# These use /s/ as a shorthand for /sites/ and include an encoded sharing ID
# Example: https://tenant.sharepoint.com/:f:/s/BlueTide-Testing/IgC9Dx6...?e=UqiPF1
_SP_SHARING_RE = re.compile(
    r"https?://([a-zA-Z0-9-]+\.sharepoint\.com)"   # hostname
    r"/:[a-z]:/s/"                                  # sharing prefix /:f:/s/, /:w:/s/, etc.
    r"([^/?#]+)"                                    # site name (e.g. BlueTide-Testing)
    r"(?:/([^?#]+))?"                               # optional encoded item ID
)

_SP_SHARED_DOCS_RE = re.compile(
    r"/Shared(?:%20|\s)Documents/(.+?)(?:\?|#|$)"
)
_SP_ID_PARAM_RE = re.compile(
    r"[?&]id=([^&#]+)"
)


def parse_drive_link(url: str) -> ParsedLink:
    """Parse a user-pasted URL into a ``ParsedLink``.

    Raises ``HTTPException(400)`` if the URL format is not recognised.
    """
    url = url.strip()

    # ── Try Google Drive ──────────────────────────────────────────────
    m = _GDRIVE_FOLDER_RE.search(url)
    if m:
        return ParsedLink(
            provider=LinkProvider.GDRIVE,
            folder_id=m.group(1),
            original_url=url,
        )

    # ── Try SharePoint (full /sites/ path) ────────────────────────────
    m = _SP_SITE_RE.search(url)
    if m:
        hostname = m.group(1)
        site_path = m.group(2)

        item_path: Optional[str] = None

        # Try to extract a folder path from the URL
        folder_m = _SP_SHARED_DOCS_RE.search(url)
        if folder_m:
            raw_folder = unquote(folder_m.group(1)).rstrip("/")
            # Strip query params that may have leaked into the path
            raw_folder = raw_folder.split("?")[0].rstrip("/")
            item_path = raw_folder or None
        else:
            id_m = _SP_ID_PARAM_RE.search(url)
            if id_m:
                raw = unquote(id_m.group(1))
                # Strip leading /sites/<Name>/Shared Documents/ if present
                docs_prefix = f"{site_path}/Shared Documents/"
                if raw.startswith(docs_prefix):
                    raw = raw[len(docs_prefix):]
                item_path = raw.rstrip("/") or None

        return ParsedLink(
            provider=LinkProvider.SHAREPOINT,
            site_hostname=hostname,
            site_path=site_path,
            item_path=item_path,
            original_url=url,
        )

    # ── Try SharePoint sharing links with /s/ shorthand ───────────────
    # These are common when users share a folder via "Copy link" in SharePoint.
    # Format: https://tenant.sharepoint.com/:f:/s/SiteName/EncodedId?e=token
    m = _SP_SHARING_RE.search(url)
    if m:
        hostname = m.group(1)
        site_name = m.group(2)
        site_path = f"/sites/{site_name}"
        # The encoded ID in sharing links is opaque — we connect to the
        # site root document library and list all files.
        return ParsedLink(
            provider=LinkProvider.SHAREPOINT,
            site_hostname=hostname,
            site_path=site_path,
            item_path=None,
            original_url=url,
        )

    # ── Generic sharepoint.com fallback ───────────────────────────────
    # If the URL contains sharepoint.com but didn't match any pattern above,
    # try to extract hostname and any /sites/ or /s/ reference.
    sp_generic = re.search(r"https?://([a-zA-Z0-9-]+\.sharepoint\.com)", url)
    if sp_generic:
        hostname = sp_generic.group(1)

        # Try to find /s/<SiteName> or /sites/<SiteName> anywhere in the URL
        site_match = re.search(r"/(?:sites|s)/([^/?#]+)", url)
        if site_match:
            site_name = site_match.group(1)
            site_path = f"/sites/{site_name}"
            return ParsedLink(
                provider=LinkProvider.SHAREPOINT,
                site_hostname=hostname,
                site_path=site_path,
                item_path=None,
                original_url=url,
            )

    # ── Unrecognised ──────────────────────────────────────────────────
    raise HTTPException(
        status_code=400,
        detail={
            "error": "UNSUPPORTED_LINK",
            "message": (
                "Could not recognise this URL. Please provide a Google Drive "
                "folder link or a SharePoint document-library link."
            ),
            "supported_formats": [
                "https://drive.google.com/drive/folders/<folder_id>",
                "https://<tenant>.sharepoint.com/sites/<site>/Shared Documents/<folder>",
                "https://<tenant>.sharepoint.com/:f:/r/sites/<site>/Shared Documents/<folder>",
                "https://<tenant>.sharepoint.com/:f:/s/<site>/<sharing_id>",
            ],
        },
    )


__all__ = ["parse_drive_link", "ParsedLink", "LinkProvider"]

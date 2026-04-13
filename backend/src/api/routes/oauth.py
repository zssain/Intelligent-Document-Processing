"""OAuth account-linking endpoints for Google Drive and SharePoint.

Provides per-user OAuth flows so each user can connect their own
Google Drive or SharePoint account.  Tokens are encrypted at rest
using Fernet and stored in Firestore under:

    tenants/{tenant_id}/user_connections/{user_uid}

Endpoints
---------
GET  /auth/gdrive/connect         → redirect to Google OAuth consent
GET  /auth/gdrive/callback        → exchange code → store tokens
GET  /auth/sharepoint/connect     → redirect to Azure AD consent
GET  /auth/sharepoint/callback    → exchange code → store tokens
GET  /auth/connections             → per-provider connection status
DELETE /auth/{provider}/disconnect → revoke / remove tokens
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from config.settings import settings, DEFAULT_TENANT_ID
from src.api.auth import CurrentUser, get_current_user
from src.utils.firebase import firestore_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Public router for OAuth callbacks – these are hit by browser redirects from
# Google/Azure, so they cannot require a Bearer token.  The ``state`` query
# parameter carries tenant_id:uid to identify the user.
public_router = APIRouter()

# ── Fernet cipher (lazy init) ─────────────────────────────────────────────
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.token_encryption_key
        if not key:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


def _build_callback_url(request: Request, route_name: str) -> str:
    """Build the OAuth callback URL.

    When ``settings.backend_public_url`` is set (recommended for Lambda / API
    Gateway / direct backend hosting), the callback URL is built from the
    backend's public base URL.

    When ``settings.frontend_url`` is set, the
    callback URL is constructed from the frontend base so that the browser
    redirect from Google/Azure goes through the frontend's nginx proxy,
    which forwards ``/api/v1/*`` to the backend.

    This guarantees the redirect_uri matches what is registered in the Cloud
    Console regardless of how the backend is addressed internally.

    When ``frontend_url`` is empty (local dev), falls back to ``request.url_for``
    with an http→https upgrade.
    """
    if settings.backend_public_url:
        base = settings.backend_public_url.rstrip("/")
        path = request.app.url_path_for(route_name)
        return f"{base}{path}"

    if settings.frontend_url:
        base = settings.frontend_url.rstrip("/")
        # route_name → URL path inside the FastAPI app
        path = request.app.url_path_for(route_name)
        return f"{base}{path}"

    # Fallback: derive from the incoming request (force https behind proxy)
    url = str(request.url_for(route_name))
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


# ── Firestore helpers ─────────────────────────────────────────────────────

def _conn_ref(tenant_id: str, uid: str):
    """Return the Firestore document reference for a user's connections."""
    return (
        firestore_client
        .collection("tenants")
        .document(tenant_id)
        .collection("user_connections")
        .document(uid)
    )


def _get_connection(tenant_id: str, uid: str) -> Dict[str, Any]:
    """Read the user_connections doc (empty dict if not found)."""
    try:
        doc = _conn_ref(tenant_id, uid).get()
        return doc.to_dict() if doc.exists else {}
    except Exception as exc:
        logger.warning("Could not read user_connections for %s: %s", uid, exc)
        return {}


def _save_connection(tenant_id: str, uid: str, data: Dict[str, Any]) -> None:
    """Merge data into the user_connections doc."""
    _conn_ref(tenant_id, uid).set(data, merge=True)


def _remove_provider(tenant_id: str, uid: str, provider: str) -> None:
    """Delete a provider's nested fields from the connections doc."""
    from google.cloud.firestore_v1 import DELETE_FIELD
    _conn_ref(tenant_id, uid).update({provider: DELETE_FIELD})


# ── Google OAuth constants ────────────────────────────────────────────────
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_SCOPES = "https://www.googleapis.com/auth/drive.readonly"


# ── Azure AD OAuth constants ─────────────────────────────────────────────
_AZURE_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_AZURE_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_AZURE_SCOPES = "https://graph.microsoft.com/Files.Read.All https://graph.microsoft.com/Sites.Read.All offline_access"


# ── OAuth success page helper ─────────────────────────────────────────────

def _oauth_success_html(provider: str) -> str:
    """Return a small HTML page that signals the opener and auto-closes."""
    label = "Google Drive" if provider == "gdrive" else "SharePoint"
    return f"""<!DOCTYPE html>
<html><head><title>Connected</title></head>
<body style="font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#0f172a;color:#e2e8f0;">
<div style="text-align:center">
  <h2 style="color:#22c55e">&#10003; {label} connected!</h2>
  <p>You can close this window.</p>
</div>
<script>
  if (window.opener) {{
    window.opener.postMessage({{ type: 'oauth-success', provider: '{provider}' }}, '*');
  }}
  setTimeout(function() {{ window.close(); }}, 2000);
</script>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════
# Google Drive
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/gdrive/connect")
async def gdrive_connect(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Redirect to Google OAuth consent screen."""
    if not settings.gdrive_oauth_client_id or not settings.gdrive_oauth_client_secret:
        raise HTTPException(
            status_code=501,
            detail="Google Drive OAuth is not configured (GDRIVE_OAUTH_CLIENT_ID / SECRET).",
        )

    # Build callback URL from the current request
    callback_url = _build_callback_url(request, "gdrive_callback")

    params = {
        "client_id": settings.gdrive_oauth_client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": _GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": f"{current_user.tenant_id}:{current_user.uid}",
    }
    url = f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"authorization_url": url}


@public_router.get("/gdrive/callback", name="gdrive_callback")
async def gdrive_callback(
    code: str = Query(...),
    state: str = Query(""),
    error: str = Query(None),
    request: Request = None,
):
    """Exchange Google auth code for tokens and store encrypted."""
    import traceback

    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    # Parse state → tenant_id:uid
    parts = state.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter")
    tenant_id, uid = parts

    try:
        callback_url = _build_callback_url(request, "gdrive_callback")
        logger.info("GDrive callback – tenant=%s, uid=%s, redirect_uri=%s", tenant_id, uid, callback_url)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.gdrive_oauth_client_id,
                    "client_secret": settings.gdrive_oauth_client_secret,
                    "redirect_uri": callback_url,
                    "grant_type": "authorization_code",
                },
            )

        if resp.status_code != 200:
            logger.error("Google token exchange failed (%s): %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail=f"Failed to exchange Google auth code: {resp.text}")

        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = int(token_data.get("expires_in", 3600))

        logger.info("Token exchange succeeded, saving connection for user %s", uid)

        _save_connection(tenant_id, uid, {
            "gdrive": {
                "status": "connected",
                "encrypted_access_token": _encrypt(access_token),
                "encrypted_refresh_token": _encrypt(refresh_token) if refresh_token else "",
                "token_expiry": datetime.now(timezone.utc).timestamp() + expires_in,
                "scopes": _GOOGLE_SCOPES,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "error_reason": None,
                "last_error_at": None,
            }
        })

        logger.info("Google Drive connected for user %s (tenant %s)", uid, tenant_id)

        # Return a page that signals the opener window and closes itself
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=_oauth_success_html("gdrive"),
            status_code=200,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "GDrive callback UNHANDLED error for user %s (tenant %s): %s\n%s",
            uid, tenant_id, exc, traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail=f"OAuth callback failed: {type(exc).__name__}: {exc}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# SharePoint / Microsoft Graph
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/sharepoint/connect")
async def sharepoint_connect(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Redirect to Azure AD OAuth consent screen."""
    if not settings.sharepoint_oauth_client_id or not settings.sharepoint_oauth_client_secret:
        raise HTTPException(
            status_code=501,
            detail="SharePoint OAuth is not configured (SHAREPOINT_OAUTH_CLIENT_ID / SECRET).",
        )

    callback_url = _build_callback_url(request, "sharepoint_callback")

    params = {
        "client_id": settings.sharepoint_oauth_client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": _AZURE_SCOPES,
        "response_mode": "query",
        "state": f"{current_user.tenant_id}:{current_user.uid}",
    }
    url = f"{_AZURE_AUTH_URL}?{urlencode(params)}"
    return {"authorization_url": url}


@public_router.get("/sharepoint/callback", name="sharepoint_callback")
async def sharepoint_callback(
    code: str = Query(...),
    state: str = Query(""),
    error: str = Query(None),
    error_description: str = Query(None),
    request: Request = None,
):
    """Exchange Azure AD auth code for tokens and store encrypted."""
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Azure AD OAuth error: {error} — {error_description}",
        )

    parts = state.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter")
    tenant_id, uid = parts

    callback_url = _build_callback_url(request, "sharepoint_callback")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _AZURE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.sharepoint_oauth_client_id,
                "client_secret": settings.sharepoint_oauth_client_secret,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
                "scope": _AZURE_SCOPES,
            },
        )

    if resp.status_code != 200:
        logger.error("Azure AD token exchange failed: %s", resp.text)
        raise HTTPException(status_code=502, detail="Failed to exchange Azure AD auth code")

    token_data = resp.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = int(token_data.get("expires_in", 3600))

    _save_connection(tenant_id, uid, {
        "sharepoint": {
            "status": "connected",
            "encrypted_access_token": _encrypt(access_token),
            "encrypted_refresh_token": _encrypt(refresh_token) if refresh_token else "",
            "token_expiry": datetime.now(timezone.utc).timestamp() + expires_in,
            "scopes": _AZURE_SCOPES,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "error_reason": None,
            "last_error_at": None,
        }
    })

    logger.info("SharePoint connected for user %s (tenant %s)", uid, tenant_id)

    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content=_oauth_success_html("sharepoint"),
        status_code=200,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Connection status & disconnect
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/connections")
async def get_connections(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return connection status for each provider (never exposes tokens)."""
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    conn = _get_connection(tenant_id, current_user.uid)

    # Check whether OAuth credentials are configured on the server
    gdrive_configured = bool(
        settings.gdrive_oauth_client_id and settings.gdrive_oauth_client_secret
    )
    sharepoint_oauth_configured = bool(
        settings.sharepoint_oauth_client_id and settings.sharepoint_oauth_client_secret
    )
    # SharePoint can also work with app-only (client_credentials) auth
    sharepoint_app_configured = bool(
        settings.sharepoint_tenant_id
        and settings.sharepoint_client_id
        and settings.sharepoint_client_secret
    )
    oauth_configured = {
        "gdrive": gdrive_configured,
        "sharepoint": sharepoint_oauth_configured or sharepoint_app_configured,
    }

    result: Dict[str, Dict[str, Any]] = {}
    for provider in ("gdrive", "sharepoint"):
        prov_data = conn.get(provider, {})
        if prov_data:
            status = prov_data.get("status", "disconnected")
            result[provider] = {
                "status": status,
                "connected": status == "connected",
                "connected_at": prov_data.get("connected_at"),
                "scopes": prov_data.get("scopes"),
                "error_reason": prov_data.get("error_reason"),
                "last_error_at": prov_data.get("last_error_at"),
                "oauth_configured": oauth_configured[provider],
            }
        else:
            result[provider] = {
                "status": "disconnected",
                "connected": False,
                "oauth_configured": oauth_configured[provider],
            }

    # SharePoint: also report app-only auth mode so frontend can show
    # appropriate UX (connect-via-link works without per-user OAuth).
    result["sharepoint"]["app_configured"] = sharepoint_app_configured
    result["sharepoint"]["auth_mode"] = (
        "oauth" if sharepoint_oauth_configured
        else "app_only" if sharepoint_app_configured
        else "none"
    )

    # S3 is always org-level (no per-user auth)
    result["s3"] = {"status": "org_configured", "connected": True}

    return result


@router.delete("/{provider}/disconnect")
async def disconnect_provider(
    provider: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Remove stored tokens for a provider."""
    if provider not in ("gdrive", "sharepoint"):
        raise HTTPException(status_code=400, detail="Invalid provider. Use 'gdrive' or 'sharepoint'.")

    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    _remove_provider(tenant_id, current_user.uid, provider)
    logger.info("Disconnected %s for user %s (tenant %s)", provider, current_user.uid, tenant_id)
    return {"status": "disconnected", "provider": provider}


# ═══════════════════════════════════════════════════════════════════════════
# Token refresh helpers (used by connectors / job manager)
# ═══════════════════════════════════════════════════════════════════════════

_HARD_FAILURE_CODES = {"invalid_grant", "interaction_required", "consent_required"}


async def refresh_google_token(tenant_id: str, uid: str) -> Optional[str]:
    """Refresh a user's Google access token.  Returns the new token or None.

    On hard failure (revoked / invalid_grant) the connection is auto-disconnected.
    """
    conn = _get_connection(tenant_id, uid)
    gdrive = conn.get("gdrive", {})
    if not gdrive or gdrive.get("status") != "connected":
        return None

    encrypted_rt = gdrive.get("encrypted_refresh_token", "")
    if not encrypted_rt:
        return None

    refresh_token = _decrypt(encrypted_rt)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.gdrive_oauth_client_id,
                "client_secret": settings.gdrive_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        new_access = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        _save_connection(tenant_id, uid, {
            "gdrive": {
                "encrypted_access_token": _encrypt(new_access),
                "token_expiry": datetime.now(timezone.utc).timestamp() + expires_in,
                "error_reason": None,
                "last_error_at": None,
            }
        })
        return new_access

    # Check for hard failure
    error_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    error_code = error_body.get("error", "")

    if error_code in _HARD_FAILURE_CODES:
        logger.warning(
            "Google refresh token revoked/expired for user %s: %s",
            uid, error_code,
        )
        _save_connection(tenant_id, uid, {
            "gdrive": {
                "status": "disconnected",
                "error_reason": error_code,
                "last_error_at": datetime.now(timezone.utc).isoformat(),
            }
        })
        return None

    # Transient failure — caller should retry
    logger.warning("Google token refresh failed (%s): %s", resp.status_code, resp.text[:200])
    return None


async def refresh_sharepoint_token(tenant_id: str, uid: str) -> Optional[str]:
    """Refresh a user's SharePoint/Graph access token.  Returns new token or None.

    On hard failure the connection is auto-disconnected.
    """
    conn = _get_connection(tenant_id, uid)
    sp = conn.get("sharepoint", {})
    if not sp or sp.get("status") != "connected":
        return None

    encrypted_rt = sp.get("encrypted_refresh_token", "")
    if not encrypted_rt:
        return None

    refresh_token = _decrypt(encrypted_rt)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _AZURE_TOKEN_URL,
            data={
                "client_id": settings.sharepoint_oauth_client_id,
                "client_secret": settings.sharepoint_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "scope": _AZURE_SCOPES,
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        new_access = data["access_token"]
        new_refresh = data.get("refresh_token", refresh_token)
        expires_in = int(data.get("expires_in", 3600))
        _save_connection(tenant_id, uid, {
            "sharepoint": {
                "encrypted_access_token": _encrypt(new_access),
                "encrypted_refresh_token": _encrypt(new_refresh),
                "token_expiry": datetime.now(timezone.utc).timestamp() + expires_in,
                "error_reason": None,
                "last_error_at": None,
            }
        })
        return new_access

    error_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    error_code = error_body.get("error", "")

    if error_code in _HARD_FAILURE_CODES:
        logger.warning(
            "SharePoint refresh token revoked/expired for user %s: %s",
            uid, error_code,
        )
        _save_connection(tenant_id, uid, {
            "sharepoint": {
                "status": "disconnected",
                "error_reason": error_code,
                "last_error_at": datetime.now(timezone.utc).isoformat(),
            }
        })
        return None

    logger.warning("SharePoint token refresh failed (%s): %s", resp.status_code, resp.text[:200])
    return None


def get_decrypted_access_token(tenant_id: str, uid: str, provider: str) -> Optional[str]:
    """Return the decrypted access token for a provider, or None if disconnected."""
    conn = _get_connection(tenant_id, uid)
    prov = conn.get(provider, {})
    if not prov or prov.get("status") != "connected":
        return None
    encrypted = prov.get("encrypted_access_token", "")
    if not encrypted:
        return None
    return _decrypt(encrypted)

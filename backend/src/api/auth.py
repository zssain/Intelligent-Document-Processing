"""Firebase-backed authentication & authorisation layer.

Provides:
    get_current_user   – FastAPI dependency that verifies a Firebase ID-token
                         from the ``Authorization: Bearer <token>`` header,
                         enriches it with Firestore user-profile data, and
                         returns a ``CurrentUser`` dataclass.
    require_role       – dependency factory that raises 403 if the user's role
                         does not match the required role.
    require_source_permission – dependency factory that raises 403 if the user
                         lacks a specific action on a specific source.
    get_user_doc_filter – returns ``None`` (admin – no filter) or a dict with
                         ``clearance_level``, ``allowed_category_ids``, and
                         ``allowed_sources`` for row-level document access
                         control.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth

from src.utils.firebase import get_firestore_client, initialize_firebase

logger = logging.getLogger(__name__)

# Ensure Firebase Admin SDK is initialised before first use.
initialize_firebase()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
# Default source permissions for new users (view-only on all sources)
DEFAULT_SOURCE_PERMISSIONS: Dict[str, Dict[str, bool]] = {
    "s3":            {"can_view": True,  "can_download": False, "can_filter": True,  "can_sync": False, "can_preview": True},
    "sharepoint":    {"can_view": True,  "can_download": False, "can_filter": True,  "can_sync": False, "can_preview": True},
    "gdrive":        {"can_view": True,  "can_download": False, "can_filter": True,  "can_sync": False, "can_preview": True},
    "direct_upload": {"can_view": True,  "can_download": False, "can_filter": True,  "can_sync": False, "can_preview": True},
}

# Admin gets everything
ADMIN_SOURCE_PERMISSIONS: Dict[str, Dict[str, bool]] = {
    source: {action: True for action in ["can_view", "can_download", "can_filter", "can_sync", "can_preview"]}
    for source in ["s3", "sharepoint", "gdrive", "direct_upload"]
}

SOURCES = ["s3", "sharepoint", "gdrive", "direct_upload"]
ACTIONS = ["can_view", "can_download", "can_filter", "can_sync", "can_preview"]


@dataclass
class CurrentUser:
    """Authenticated user context attached to every request."""

    uid: str
    tenant_id: str
    role: str
    clearance_level: int
    allowed_category_ids: List[str] = field(default_factory=list)
    source_permissions: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role in ("org_admin", "admin")

    @property
    def allowed_sources(self) -> List[str]:
        """Sources where the user has can_view == True."""
        if self.is_admin:
            return SOURCES[:]
        return [
            source for source, perms in self.source_permissions.items()
            if perms.get("can_view", False)
        ]

    def has_source_permission(self, source: str, action: str) -> bool:
        """Check if user has a specific action on a specific source."""
        if self.is_admin:
            return True
        return self.source_permissions.get(source, {}).get(action, False)


# ---------------------------------------------------------------------------
# Core dependency – token verification + Firestore enrichment
# ---------------------------------------------------------------------------
async def get_current_user(request: Request) -> CurrentUser:
    """Verify the Firebase ID-token and build a ``CurrentUser``.

    Steps
    -----
    1. Extract the Bearer token from the ``Authorization`` header.
    2. Call ``firebase_admin.auth.verify_id_token()`` → decoded claims.
    3. Read custom claims: ``uid``, ``tenant_id``, ``role``,
       ``clearance_level``.
    4. Fetch ``tenants/{tenant_id}/users/{uid}`` from Firestore to obtain
       ``allowed_category_ids`` and ``is_active``.
    5. Return a ``CurrentUser`` dataclass.

    Raises
    ------
    HTTPException 401 – missing / invalid / expired token.
    HTTPException 403 – user account is deactivated (``is_active == false``).
    """

    # 1. Extract token -------------------------------------------------------
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
        )

    token = auth_header.split(" ", 1)[1]

    # 2. Verify token --------------------------------------------------------
    try:
        decoded = firebase_auth.verify_id_token(token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token has expired. Please re-authenticate.",
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token has been revoked.",
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token.",
        )
    except Exception as exc:
        logger.error("Unexpected error verifying ID token: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify ID token.",
        )

    # 3. Extract custom claims -----------------------------------------------
    uid: str = decoded["uid"]
    tenant_id: str = decoded.get("tenant_id", "")
    role: str = decoded.get("role", "viewer")
    clearance_level: int = int(decoded.get("clearance_level", 0))

    # 4. Fetch Firestore user profile ----------------------------------------
    allowed_category_ids: List[str] = []
    source_permissions: Dict[str, Dict[str, bool]] = {}
    is_active: bool = True

    try:
        fs = get_firestore_client()
        user_ref = fs.collection("tenants").document(tenant_id).collection("users").document(uid)
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            allowed_category_ids = user_data.get("allowed_category_ids", [])
            is_active = user_data.get("is_active", True)
            source_permissions = user_data.get("source_permissions", {})
        else:
            # Auto-create Firestore profile on first login
            logger.info(
                "Auto-creating Firestore profile for uid=%s tenant=%s role=%s",
                uid, tenant_id, role,
            )
            try:
                # Try to get extra info from Firebase Auth
                fb_user = firebase_auth.get_user(uid)
                email = fb_user.email or ""
                display_name = fb_user.display_name or ""
            except Exception:
                email = decoded.get("email", "")
                display_name = decoded.get("name", "")

            profile_data = {
                "uid": uid,
                "email": email,
                "display_name": display_name,
                "role": role,
                "clearance_level": clearance_level,
                "allowed_category_ids": [],
                "source_permissions": DEFAULT_SOURCE_PERMISSIONS.copy() if role not in ("org_admin", "admin") else ADMIN_SOURCE_PERMISSIONS.copy(),
                "is_active": True,
                "created_at": decoded.get("auth_time", ""),
            }
            user_ref.set(profile_data)
            source_permissions = profile_data["source_permissions"]
    except Exception as exc:
        # Non-fatal: log and continue with claim-only data
        logger.error(
            "Failed to fetch Firestore user profile for uid=%s: %s",
            uid,
            exc,
            exc_info=True,
        )

    # Resolve effective source permissions
    if role in ("org_admin", "admin"):
        effective_permissions = ADMIN_SOURCE_PERMISSIONS.copy()
    elif source_permissions:
        effective_permissions = source_permissions
    else:
        effective_permissions = DEFAULT_SOURCE_PERMISSIONS.copy()

    # 5. Active-user gate ----------------------------------------------------
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact your organisation admin.",
        )

    return CurrentUser(
        uid=uid,
        tenant_id=tenant_id,
        role=role,
        clearance_level=clearance_level,
        allowed_category_ids=allowed_category_ids,
        source_permissions=effective_permissions,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# Role guard – dependency factory
# ---------------------------------------------------------------------------
def require_role(required_role: str) -> Callable:
    """Return a FastAPI dependency that raises 403 unless the user has *required_role*.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_role("org_admin"))])
        async def admin_endpoint(): ...
    """

    async def _check_role(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required. You have '{current_user.role}'.",
            )
        return current_user

    return _check_role


# ---------------------------------------------------------------------------
# Source permission guard – dependency factory
# ---------------------------------------------------------------------------
def require_source_permission(source: str, action: str) -> Callable:
    """Return a FastAPI dependency that raises 403 unless the user has
    *action* on *source*.

    Usage::

        @router.get("/s3/list",
                    dependencies=[Depends(require_source_permission("s3", "can_view"))])
        async def list_s3(): ...
    """

    async def _check_permission(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_source_permission(source, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have '{action}' permission on '{source}'.",
            )
        return current_user

    return _check_permission


# ---------------------------------------------------------------------------
# Document-level access filter
# ---------------------------------------------------------------------------
def get_user_doc_filter(
    user: CurrentUser,
) -> Optional[Dict[str, Any]]:
    """Return a document-access filter dict, or ``None`` for admins.

    * **org_admin** / **admin** → ``None`` (unrestricted access).
    * Everyone else → ``{ "clearance_level": <int>, "allowed_category_ids": [...], "allowed_sources": [...] }``.
    """

    if user.is_admin:
        return None

    return {
        "clearance_level": user.clearance_level,
        "allowed_category_ids": user.allowed_category_ids,
        "allowed_sources": user.allowed_sources,
    }

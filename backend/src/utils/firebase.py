"""
Firebase Admin SDK initialization and utilities for backend services.
"""
import base64
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import lru_cache
import os
from pathlib import Path
from config.settings import settings


# Initialize Firebase Admin SDK
_app = None
_firestore_client = None
_auth_client = None


def _resolve_firebase_credentials_path() -> str:
    """Ensure a service-account JSON exists when only base64 is provided."""
    if settings.firebase_service_account_key_path:
        target_path = Path(settings.firebase_service_account_key_path)
    else:
        target_path = Path("/tmp/firebase-sa.json")

    firebase_b64 = (os.getenv("FIREBASE_SERVICE_ACCOUNT_B64", "")).strip()
    if firebase_b64 and not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(base64.b64decode(firebase_b64))

    return str(target_path)


def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    global _app, _firestore_client, _auth_client
    
    if _app is None:
        # Load service account credentials
        cred = credentials.Certificate(_resolve_firebase_credentials_path())
        _app = firebase_admin.initialize_app(cred)
        _firestore_client = firestore.client()
        _auth_client = auth
    
    return _app


@lru_cache()
def get_firestore_client():
    """Get the Firestore client instance."""
    if _firestore_client is None:
        initialize_firebase()
    return _firestore_client


@lru_cache()
def get_auth_client():
    """Get the Firebase Auth client."""
    if _auth_client is None:
        initialize_firebase()
    return _auth_client


# Export initialized clients
firestore_client = get_firestore_client()
auth = get_auth_client()

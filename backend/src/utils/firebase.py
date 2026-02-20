"""
Firebase Admin SDK initialization and utilities for backend services.
"""
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import lru_cache
from config.settings import settings, DEFAULT_TENANT_ID


# Initialize Firebase Admin SDK
_app = None
_firestore_client = None
_auth_client = None


def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    global _app, _firestore_client, _auth_client
    
    if _app is None:
        # Load service account credentials
        cred = credentials.Certificate(settings.firebase_service_account_key_path)
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

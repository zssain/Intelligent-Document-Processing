#!/usr/bin/env python3
"""
Seed script to create an admin user in Firebase.

Usage:
    python scripts/seed_admin.py --email admin@example.com
    python scripts/seed_admin.py --uid abc123def456

This script:
1. Sets custom claims (tenant_id, role="org_admin", clearance_level=3)
2. Creates/updates the Firestore user document with admin privileges
"""
import argparse
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from src.utils.firebase import firestore_client, auth
from config.settings import DEFAULT_TENANT_ID
from datetime import datetime


def seed_admin(email: str = None, uid: str = None):
    """
    Seed an admin user by setting custom claims and Firestore document.
    
    Args:
        email: User email address (will lookup UID)
        uid: User UID (direct lookup)
    """
    if not email and not uid:
        raise ValueError("Either email or uid must be provided")
    
    try:
        # Get user UID
        if email:
            print(f"Looking up user by email: {email}")
            user = auth.get_user_by_email(email)
            uid = user.uid
            print(f"Found user with UID: {uid}")
        else:
            print(f"Looking up user by UID: {uid}")
            user = auth.get_user(uid)
            email = user.email
            print(f"Found user with email: {email}")
        
        # Set custom claims
        custom_claims = {
            "tenant_id": DEFAULT_TENANT_ID,
            "role": "org_admin",
            "clearance_level": 3,
        }
        
        print(f"Setting custom claims: {custom_claims}")
        auth.set_custom_user_claims(uid, custom_claims)
        print("✓ Custom claims set successfully")
        
        # Update Firestore user document
        user_doc_ref = (
            firestore_client
            .collection("tenants")
            .document(DEFAULT_TENANT_ID)
            .collection("users")
            .document(uid)
        )
        
        user_data = {
            "email": email or "",
            "display_name": user.display_name or "",
            "role": "org_admin",
            "clearance_level": 3,
            "allowed_category_ids": [],  # Admins can see all categories
            "is_active": True,
            "updated_at": datetime.utcnow(),
        }
        
        # Check if document exists
        doc = user_doc_ref.get()
        if doc.exists:
            print(f"Updating existing user document...")
            user_doc_ref.update(user_data)
            print("✓ User document updated")
        else:
            print(f"Creating new user document...")
            user_data["created_at"] = datetime.utcnow()
            user_doc_ref.set(user_data)
            print("✓ User document created")
        
        print(f"\n✅ Successfully seeded admin user:")
        print(f"   Email: {email}")
        print(f"   UID: {uid}")
        print(f"   Role: org_admin")
        print(f"   Clearance Level: 3")
        print(f"   Tenant: {DEFAULT_TENANT_ID}")
        
    except Exception as e:
        print(f"❌ Error seeding admin user: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Seed an admin user in Firebase"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--email",
        help="User email address"
    )
    group.add_argument(
        "--uid",
        help="User UID"
    )
    
    args = parser.parse_args()
    seed_admin(email=args.email, uid=args.uid)


if __name__ == "__main__":
    main()

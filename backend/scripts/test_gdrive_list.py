#!/usr/bin/env python3
"""Quick smoke test: list PDFs in the configured Google Drive folder.

Usage (from the backend/ directory):

    uv run python scripts/test_gdrive_list.py
    # or, if the API server is running:
    uv run python scripts/test_gdrive_list.py --via-api

Two modes:
  1. **Direct** (default) – instantiates GoogleDriveClient locally and calls
     list_folder_pdfs.  No API server required.
  2. **Via API** – calls GET /api/v1/datalake/gdrive/list on localhost.
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure backend/ is on sys.path when run from backend/scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _direct():
    from src.connectors.google_drive import GoogleDriveClient
    from config.settings import settings

    client = GoogleDriveClient()
    folder_id = settings.gdrive_folder_id
    if not folder_id:
        print("❌ GDRIVE_FOLDER_ID is not set. Cannot list files.")
        sys.exit(1)

    print(f"Folder ID: {folder_id}")
    files = client.list_folder_pdfs(folder_id, limit=20)
    print(f"\n✅ Found {len(files)} PDFs under folder '{folder_id}':\n")
    for f in files:
        size_kb = int(f.get("size", 0)) / 1024
        modified = f.get("modifiedTime", "?")
        print(f"  • {f['name']}  ({size_kb:.1f} KB)  id={f['id']}  modified={modified}")


def _via_api():
    import requests

    base = os.getenv("API_BASE", "http://localhost:8000")
    api_key = os.getenv("X_API_KEY", "")
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    resp = requests.get(
        f"{base}/api/v1/datalake/gdrive/list",
        params={"limit": 20},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    print(f"✅ {body['total_pdfs']} PDFs in folder '{body['folder_id']}':")
    for p in body["pdfs"]:
        print(f"  • {p['name']}  ({p['size']} B)  id={p['file_id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--via-api", action="store_true")
    args = parser.parse_args()

    if args.via_api:
        _via_api()
    else:
        _direct()

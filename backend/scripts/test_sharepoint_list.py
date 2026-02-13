#!/usr/bin/env python3
"""Quick smoke test: list PDFs in the configured SharePoint folder.

Usage (from the backend/ directory):

    uv run python scripts/test_sharepoint_list.py
    # or, if the API server is running:
    uv run python scripts/test_sharepoint_list.py --via-api

Two modes:
  1. **Direct** (default) – instantiates GraphClient locally and calls
     list_folder_children.  No API server required.
  2. **Via API** – calls GET /api/v1/datalake/sharepoint/list on localhost.
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure backend/ is on sys.path when run from backend/scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _direct():
    from src.connectors.sharepoint_graph import GraphClient

    graph = GraphClient()
    site_id, drive_id = graph.get_site_and_drive()
    print(f"Site ID : {site_id}")
    print(f"Drive ID: {drive_id}")

    from config.settings import settings

    items = graph.list_folder_children(
        drive_id, settings.sharepoint_folder_path, max_items=20
    )
    pdfs = [i for i in items if i.get("name", "").lower().endswith(".pdf")]
    print(f"\n✅ Found {len(pdfs)} PDFs (of {len(items)} total items) under "
          f"'{settings.sharepoint_folder_path}':\n")
    for p in pdfs:
        size_kb = p.get("size", 0) / 1024
        print(f"  • {p['name']}  ({size_kb:.1f} KB)  id={p['id']}")


def _via_api():
    import requests

    base = os.getenv("API_BASE", "http://localhost:8000")
    api_key = os.getenv("X_API_KEY", "")
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    resp = requests.get(
        f"{base}/api/v1/datalake/sharepoint/list",
        params={"limit": 20},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    print(f"✅ {body['total_pdfs']} PDFs in '{body['folder_path']}':")
    for p in body["pdfs"]:
        print(f"  • {p['name']}  ({p['size']} B)  id={p['item_id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--via-api", action="store_true")
    args = parser.parse_args()

    if args.via_api:
        _via_api()
    else:
        _direct()

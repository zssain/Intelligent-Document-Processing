#!/usr/bin/env python3
"""Acceptance test: call the Google Drive sync endpoint and verify results.

Usage (backend server must be running on localhost:8000):

    uv run python scripts/test_gdrive_sync.py

Set API_BASE / X_API_KEY env vars to override defaults.
"""

from __future__ import annotations

import os
import sys
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("X_API_KEY", "")
HEADERS = {}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


# ---------------------------------------------------------------------------
# Test 1 – List works
# ---------------------------------------------------------------------------
def test_list():
    print("\n── 1. Google Drive list ──")
    resp = requests.get(
        _url("/api/v1/datalake/gdrive/list"),
        headers=HEADERS,
        params={"limit": 10},
        timeout=30,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "total_pdfs" in body
    print(f"  ✅ list returned {body['total_pdfs']} PDFs "
          f"(folder={body.get('folder_id', '?')})")
    return body


# ---------------------------------------------------------------------------
# Test 2 – Sync completes
# ---------------------------------------------------------------------------
def test_sync():
    print("\n── 2. Google Drive sync ──")
    resp = requests.post(
        _url("/api/v1/datalake/gdrive/sync"),
        headers=HEADERS,
        params={"limit": 3},
        timeout=300,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "completed"
    print(f"  ✅ sync completed – ingested={body['ingested']}, "
          f"skipped={body['skipped']}, updated={body.get('updated', 0)}, "
          f"failed={body['failed']}, used_changes_api={body.get('used_changes_api')}")
    return body


# ---------------------------------------------------------------------------
# Test 3 – Idempotent (second sync skips)
# ---------------------------------------------------------------------------
def test_idempotent():
    print("\n── 3. Idempotent re-sync ──")
    resp = requests.post(
        _url("/api/v1/datalake/gdrive/sync"),
        headers=HEADERS,
        params={"limit": 3, "force": False},
        timeout=300,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["ingested"] == 0, (
        f"Expected 0 newly ingested (idempotent) but got {body['ingested']}"
    )
    print(f"  ✅ idempotent: ingested=0, skipped={body['skipped']}")
    return body


# ---------------------------------------------------------------------------
# Test 4 – Force re-processes
# ---------------------------------------------------------------------------
def test_force():
    print("\n── 4. Force re-process ──")
    resp = requests.post(
        _url("/api/v1/datalake/gdrive/sync"),
        headers=HEADERS,
        params={"limit": 1, "force": True, "full_scan": True},
        timeout=300,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    reprocessed = body.get("ingested", 0) + body.get("updated", 0)
    if body["total_pdfs"] > 0:
        assert reprocessed >= 1 or body["failed"] >= 1
    print(f"  ✅ force: ingested={body['ingested']}, "
          f"updated={body.get('updated', 0)}, failed={body['failed']}")
    return body


# ---------------------------------------------------------------------------
def main():
    tests = [
        ("list", test_list),
        ("sync", test_sync),
        ("idempotent", test_idempotent),
        ("force", test_force),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as exc:
            print(f"  ❌ FAILED: {exc}")

    print(f"\n{'='*40}")
    print(f"Results: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)


if __name__ == "__main__":
    main()

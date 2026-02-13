#!/usr/bin/env python3
"""Acceptance tests for the datalake S3 integration.

Run from the ``backend/`` directory:

    uv run python tests/test_datalake_s3.py          # standalone
    uv run pytest tests/test_datalake_s3.py -v        # via pytest

The tests hit the *real* API (localhost:8000) so the backend must be running.
Set the environment variable ``API_BASE`` to override the base URL.
Set ``X_API_KEY`` if the server has ``API_KEY`` configured.
"""

from __future__ import annotations

import os
import sys
import time
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("X_API_KEY", "")

HEADERS = {}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


# ---------------------------------------------------------------------------
# Test 1 – S3 list works for datalake prefix
# ---------------------------------------------------------------------------
def test_list_datalake_pdfs():
    """GET /api/v1/datalake/s3/list returns a well-formed response."""
    resp = requests.get(
        _url("/api/v1/datalake/s3/list"),
        headers=HEADERS,
        params={"limit": 10},
        timeout=30,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "total_pdfs" in body, f"Missing 'total_pdfs' in response: {body}"
    assert "pdfs" in body, f"Missing 'pdfs' in response: {body}"
    assert isinstance(body["pdfs"], list)
    print(f"  ✅ list returned {body['total_pdfs']} PDFs out of {body['total_objects']} total objects")
    return body


# ---------------------------------------------------------------------------
# Test 2 – sync completes without crash (ingested >= 0)
# ---------------------------------------------------------------------------
def test_sync_runs():
    """POST /api/v1/datalake/s3/sync ingests or skips without crashing."""
    resp = requests.post(
        _url("/api/v1/datalake/s3/sync"),
        headers=HEADERS,
        params={"limit": 3},  # keep small for a test run
        timeout=300,          # CU + embedding can be slow
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "completed", f"Unexpected status: {body}"
    assert body.get("ingested", 0) >= 0
    print(f"  ✅ sync completed – ingested={body['ingested']}, skipped={body['skipped']}, "
          f"updated={body.get('updated', 0)}, failed={body['failed']}")
    return body


# ---------------------------------------------------------------------------
# Test 3 – repeated sync skips already ingested objects (idempotent)
# ---------------------------------------------------------------------------
def test_sync_is_idempotent():
    """A second sync with the same data should skip everything (force=false)."""
    resp = requests.post(
        _url("/api/v1/datalake/s3/sync"),
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
# Test 4 – force=true re-processes
# ---------------------------------------------------------------------------
def test_sync_force_reprocesses():
    """With force=true, previously-ingested documents are re-processed."""
    resp = requests.post(
        _url("/api/v1/datalake/s3/sync"),
        headers=HEADERS,
        params={"limit": 1, "force": True},
        timeout=300,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    reprocessed = body.get("ingested", 0) + body.get("updated", 0)
    # If there are PDFs, at least one should have been re-processed
    if body["total_pdfs"] > 0:
        assert reprocessed >= 1 or body["failed"] >= 1, (
            f"Expected at least 1 re-processed or 1 failed when force=true, got {body}"
        )
    print(f"  ✅ force sync: ingested={body['ingested']}, updated={body.get('updated', 0)}, "
          f"failed={body['failed']}")
    return body


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    tests = [
        ("1. S3 list works", test_list_datalake_pdfs),
        ("2. sync runs without crash", test_sync_runs),
        ("3. sync is idempotent", test_sync_is_idempotent),
        ("4. force re-processes", test_sync_force_reprocesses),
    ]
    passed = 0
    for name, fn in tests:
        print(f"\n── {name} ──")
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

"""Runtime bootstrap helpers shared by Lambda entry points."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_TMP_DIRS = (
    "/tmp/data/raw",
    "/tmp/data/processed",
    "/tmp/data/raw_cu",
    "/tmp/data/normalized",
    "/tmp/data/vector_store",
    "/tmp/logs",
)


def bootstrap_runtime() -> None:
    """Prepare writable directories and Firebase credentials for Lambda."""
    for directory in _TMP_DIRS:
        Path(directory).mkdir(parents=True, exist_ok=True)

    firebase_b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64", "").strip()
    firebase_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "/tmp/firebase-sa.json")

    if firebase_b64:
        target = Path(firebase_path)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(firebase_b64))
            logger.info("Firebase service account written to %s", target)
        os.environ["FIREBASE_SERVICE_ACCOUNT_KEY_PATH"] = str(target)
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(target))
    elif firebase_path:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", firebase_path)

#!/usr/bin/env bash
set -euo pipefail

# ── Decode Firebase service-account JSON from env var ────────────
# App Runner doesn't support file mounts, so we pass the JSON key as a
# base64-encoded environment variable and decode it here at startup.
if [ -n "${FIREBASE_SERVICE_ACCOUNT_B64:-}" ]; then
    echo "$FIREBASE_SERVICE_ACCOUNT_B64" | base64 -d > /app/firebase-sa.json
    export FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/app/firebase-sa.json
    export GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-sa.json
    echo "✅ Firebase service account key written to /app/firebase-sa.json"
fi

# ── Run Alembic migrations (optional, controlled by env var) ─────
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "🔄 Running database migrations..."
    python -m alembic upgrade head
    echo "✅ Migrations complete."
fi

# ── Start the API server ─────────────────────────────────────────
echo "🚀 Starting BlueTide API on port ${PORT:-8000}..."
exec python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-2}" \
    --log-level "${LOG_LEVEL:-info}"

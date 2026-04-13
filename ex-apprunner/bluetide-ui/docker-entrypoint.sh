#!/bin/sh
set -e

# ── Generate nginx config from template ──────────────────────────
# If BACKEND_URL is set, use envsubst to inject it into nginx.conf.template
# Otherwise, fall back to the basic nginx.conf (no API proxy)
if [ -n "${BACKEND_URL:-}" ]; then
    # Normalize: strip trailing slashes (critical for nginx proxy_pass to
    # forward /api/v1/... as-is instead of stripping the /api/ prefix)
    BACKEND_URL="${BACKEND_URL%/}"
    export BACKEND_URL
    echo "✅ BACKEND_URL is set: ${BACKEND_URL}"
    echo "   Generating nginx config with API proxy..."
    # Only substitute BACKEND_URL — leave other $variables for Nginx
    envsubst '$BACKEND_URL' < /etc/nginx/templates/default.conf.template \
        > /etc/nginx/conf.d/default.conf
    echo "✅ Nginx config generated with API proxy → ${BACKEND_URL}"
    echo "   Verifying generated config..."
    cat /etc/nginx/conf.d/default.conf | grep -A3 "proxy_pass" || true
else
    echo "⚠️  BACKEND_URL not set — running without API proxy."
    echo "   Frontend will use VITE_API_URL baked at build time."
fi

# ── Hand off to the CMD ──────────────────────────────────────────
exec "$@"

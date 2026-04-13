#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# BlueTide – Deploy to AWS App Runner via ECR
# Usage:
#   ./ex-apprunner/deploy-apprunner.sh backend
#   ./ex-apprunner/deploy-apprunner.sh frontend
#   ./ex-apprunner/deploy-apprunner.sh all
#   ./ex-apprunner/deploy-apprunner.sh backend deploy
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ── Configuration ────────────────────────────────────────────────
# Override these via env vars or edit here
AWS_REGION="${AWS_REGION:-ap-south-1}"
AWS_ACCOUNT="${AWS_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo '')}"
ECR_BACKEND="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/bluetide/backend"
ECR_FRONTEND="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/bluetide/frontend"
PLATFORM="linux/amd64"

# App Runner Service ARNs (set these after first deployment)
BACKEND_SERVICE_ARN="${BACKEND_SERVICE_ARN:-}"
FRONTEND_SERVICE_ARN="${FRONTEND_SERVICE_ARN:-}"

# Frontend build args (override via env vars)
# VITE_API_URL is relative (/api/v1) — Nginx proxies to BACKEND_URL at runtime
VITE_API_URL="${VITE_API_URL:-/api/v1}"
VITE_FIREBASE_API_KEY="${VITE_FIREBASE_API_KEY:-AIzaSyD8NbjzmQOhyf8lqdM7wlqkpYoFHDdfROM}"
VITE_FIREBASE_AUTH_DOMAIN="${VITE_FIREBASE_AUTH_DOMAIN:-advanced-idp.firebaseapp.com}"
VITE_FIREBASE_PROJECT_ID="${VITE_FIREBASE_PROJECT_ID:-advanced-idp}"
VITE_FIREBASE_STORAGE_BUCKET="${VITE_FIREBASE_STORAGE_BUCKET:-advanced-idp.firebasestorage.app}"
VITE_FIREBASE_APP_ID="${VITE_FIREBASE_APP_ID:-1:353590867679:web:27b6c816ad32d248975b6a}"

# ── Helpers ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; exit 1; }

ecr_login() {
    echo "🔐 Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin \
        "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    info "ECR login successful"
}

# ── Build & Push Backend ─────────────────────────────────────────
build_backend() {
    echo ""
    echo "🏗️  Building Backend Docker image..."

    docker build --platform "$PLATFORM" \
        -f "$REPO_ROOT/ex-apprunner/backend/Dockerfile.apprunner" \
        -t bluetide-backend \
        "$REPO_ROOT"
    docker tag bluetide-backend:latest "${ECR_BACKEND}:latest"

    echo "📤 Pushing to ECR..."
    docker push "${ECR_BACKEND}:latest"
    info "Backend image pushed to ${ECR_BACKEND}:latest"
}

# ── Build & Push Frontend ────────────────────────────────────────
build_frontend() {
    if [ -z "$VITE_API_URL" ]; then
        warn "VITE_API_URL not set, defaulting to /api/v1 (Nginx proxy mode)"
        VITE_API_URL="/api/v1"
    fi

    echo ""
    echo "🏗️  Building Frontend Docker image..."

    docker build --platform "$PLATFORM" \
        -f "$REPO_ROOT/ex-apprunner/bluetide-ui/Dockerfile.apprunner" \
        --build-arg VITE_API_URL="$VITE_API_URL" \
        --build-arg VITE_FIREBASE_API_KEY="$VITE_FIREBASE_API_KEY" \
        --build-arg VITE_FIREBASE_AUTH_DOMAIN="$VITE_FIREBASE_AUTH_DOMAIN" \
        --build-arg VITE_FIREBASE_PROJECT_ID="$VITE_FIREBASE_PROJECT_ID" \
        --build-arg VITE_FIREBASE_STORAGE_BUCKET="$VITE_FIREBASE_STORAGE_BUCKET" \
        --build-arg VITE_FIREBASE_APP_ID="$VITE_FIREBASE_APP_ID" \
        -t bluetide-frontend \
        "$REPO_ROOT"

    docker tag bluetide-frontend:latest "${ECR_FRONTEND}:latest"

    echo "📤 Pushing to ECR..."
    docker push "${ECR_FRONTEND}:latest"
    info "Frontend image pushed to ${ECR_FRONTEND}:latest"
}

# ── Trigger Redeployment ─────────────────────────────────────────
trigger_deploy() {
    local service_arn="$1"
    local name="$2"
    if [ -n "$service_arn" ]; then
        echo "🚀 Triggering redeployment for ${name}..."
        aws apprunner start-deployment --service-arn "$service_arn" --region "$AWS_REGION"
        info "${name} redeployment triggered"
    else
        warn "No service ARN set for ${name}. Set ${name^^}_SERVICE_ARN to auto-deploy."
    fi
}

# ── Main ─────────────────────────────────────────────────────────
if [ -z "$AWS_ACCOUNT" ]; then
    error "AWS_ACCOUNT could not be resolved. Run 'aws configure' first."
fi

TARGET="${1:-all}"
DO_DEPLOY="${2:-}"

ecr_login

case "$TARGET" in
    backend)
        build_backend
        [ "$DO_DEPLOY" = "deploy" ] && trigger_deploy "$BACKEND_SERVICE_ARN" "Backend"
        ;;
    frontend)
        build_frontend
        [ "$DO_DEPLOY" = "deploy" ] && trigger_deploy "$FRONTEND_SERVICE_ARN" "Frontend"
        ;;
    all)
        build_backend
        build_frontend
        if [ "$DO_DEPLOY" = "deploy" ]; then
            trigger_deploy "$BACKEND_SERVICE_ARN" "Backend"
            trigger_deploy "$FRONTEND_SERVICE_ARN" "Frontend"
        fi
        ;;
    *)
        echo "Usage: $0 {backend|frontend|all} [deploy]"
        exit 1
        ;;
esac

echo ""
info "Done! 🎉"

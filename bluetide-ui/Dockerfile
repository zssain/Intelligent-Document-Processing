# ──────────────────────────────────────────────────────────────────
# BlueTide Frontend – Multi-stage build for AWS App Runner
# Stage 1: Build the React/Vite app
# Stage 2: Serve the static files with nginx
# ──────────────────────────────────────────────────────────────────

# ── Build stage ──────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .

# Build-time args – the API URL is baked into the production bundle.
# Override at build time:  docker build --build-arg VITE_API_URL=https://api.example.com/api/v1 .
ARG VITE_API_URL=/api/v1
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_APP_ID
ARG VITE_AZURE_AD_CLIENT_ID
ARG VITE_AZURE_AD_TENANT_ID

# Write build-time env vars for Vite
RUN echo "VITE_API_URL=${VITE_API_URL}" > .env.production \
    && echo "VITE_FIREBASE_API_KEY=${VITE_FIREBASE_API_KEY}" >> .env.production \
    && echo "VITE_FIREBASE_AUTH_DOMAIN=${VITE_FIREBASE_AUTH_DOMAIN}" >> .env.production \
    && echo "VITE_FIREBASE_PROJECT_ID=${VITE_FIREBASE_PROJECT_ID}" >> .env.production \
    && echo "VITE_FIREBASE_STORAGE_BUCKET=${VITE_FIREBASE_STORAGE_BUCKET}" >> .env.production \
    && echo "VITE_FIREBASE_APP_ID=${VITE_FIREBASE_APP_ID}" >> .env.production \
    && echo "VITE_AZURE_AD_CLIENT_ID=${VITE_AZURE_AD_CLIENT_ID}" >> .env.production \
    && echo "VITE_AZURE_AD_TENANT_ID=${VITE_AZURE_AD_TENANT_ID}" >> .env.production

RUN npm run build

# ── Serve stage ──────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# App Runner requires the container to listen on port 8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

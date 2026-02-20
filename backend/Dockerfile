# ──────────────────────────────────────────────────────────────────
# BlueTide Backend – Production Dockerfile for AWS App Runner
# ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# System dependencies for docling (pdf processing), tesseract (OCR),
# poppler (pdftotext), and general build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpoppler-cpp-dev \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-ara \
        libmagic1 \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python dependencies ──────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application code ────────────────────────────────────────
COPY config/ config/
COPY src/ src/
COPY alembic.ini .
COPY alembic_migrations/ alembic_migrations/

# ── Create data directories ──────────────────────────────────────
RUN mkdir -p data/raw data/processed data/raw_cu data/normalized \
             data/vector_store logs

# ── Entrypoint script ────────────────────────────────────────────
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# ── Expose port & health check ───────────────────────────────────
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]

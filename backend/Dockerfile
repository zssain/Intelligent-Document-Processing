FROM python:3.12-slim

# Use a Debian-based image so we can install the native OCR/PDF packages
# that Docling expects, while still running on Lambda via awslambdaric.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        file \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-ara \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /var/task

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir awslambdaric \
    && pip install --no-cache-dir -r requirements.txt

COPY config/ config/
COPY src/ src/
COPY lambda_handler.py jobs_handler.py runtime_bootstrap.py ./

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]

# Default command for the HTTP API Lambda. Override with
# jobs_handler.handler on the worker Lambda.
CMD ["lambda_handler.handler"]

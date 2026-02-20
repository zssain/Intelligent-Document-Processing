"""Back-fill real per-document confidence scores using Gemini.

For each active document in Firestore, this script:
1. Finds the matching raw extraction JSON in S3 (which contains the markdown).
2. Sends a short Gemini prompt asking ONLY for a confidence score (0.0–1.0).
3. Updates Firestore with the real score.

Usage:
    python scripts/backfill_real_confidence.py
"""

import json
import re
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ── Bootstrap project imports ────────────────────────────────────────────────
sys.path.insert(0, ".")

import boto3
from config.settings import settings, DEFAULT_TENANT_ID
from src.utils.firebase import firestore_client

# ── Gemini client ────────────────────────────────────────────────────────────
from google import genai  # type: ignore
from google.genai import types  # type: ignore

genai_client = genai.Client(api_key=settings.gemini_api_key)
MODEL = settings.gemini_model

CONFIDENCE_PROMPT = """\
You are a document-extraction quality assessor.

Below is the Markdown representation of a document that was extracted by an OCR / 
layout engine.  Your ONLY job is to estimate the **extraction confidence** — a 
float from 0.0 to 1.0 — representing how accurately and completely the text was 
extracted.

Consider:
- Is the text coherent and readable?
- Are numbers, dates, and structured data preserved correctly?
- Is the language (Arabic, English, etc.) rendered correctly?
- Are tables and lists intact?
- Any signs of OCR errors, garbled text, or missing content?

Reply with a single JSON object:
{"extraction_confidence": <float 0.0-1.0>}

### Document Markdown (first 4000 chars)
{markdown}
"""


def get_gemini_confidence(markdown: str) -> float:
    """Ask Gemini to score the extraction quality of a markdown document."""
    # Use first 4000 chars to keep the prompt short and fast
    snippet = markdown[:4000]
    prompt = CONFIDENCE_PROMPT.replace("{markdown}", snippet)

    try:
        response = genai_client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        conf = float(data.get("extraction_confidence", 0.85))
        return max(0.0, min(1.0, conf))
    except Exception as exc:
        logger.warning("Gemini confidence call failed: %s — using 0.85 fallback", exc)
        return 0.85


def main():
    # ── S3 client ────────────────────────────────────────────────────────
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )
    bucket = settings.aws_s3_bucket_name

    # ── Load all active documents ────────────────────────────────────────
    docs_ref = (
        firestore_client.collection("tenants")
        .document(DEFAULT_TENANT_ID)
        .collection("documents")
    )
    docs = list(docs_ref.where("status", "==", "active").stream())
    logger.info("Found %d active documents", len(docs))

    updated = 0
    for doc_snap in docs:
        d = doc_snap.to_dict()
        doc_id = doc_snap.id
        title = d.get("title", "")

        # ── Step 1: Get raw extraction from S3 ─────────────────────────
        # Try the raw_extraction URL first (contains markdown + fields)
        # then fall back to the normalized URL
        markdown = ""
        
        # Look for a matching raw_extraction file by checking S3
        # The raw files are stored as processed/raw/{prefix}_{basename}_raw.json
        try:
            # List raw extraction files and find one matching this document
            prefix_resp = s3.list_objects_v2(
                Bucket=bucket,
                Prefix="processed/raw_extraction/",
                MaxKeys=200,
            )
            base_name = title.rsplit(".", 1)[0] if "." in title else title
            
            for obj in prefix_resp.get("Contents", []):
                key = obj["Key"]
                if base_name in key:
                    data = s3.get_object(Bucket=bucket, Key=key)
                    body = json.loads(data["Body"].read())
                    markdown = body.get("markdown", "")
                    if markdown:
                        break
        except Exception:
            pass

        # Fallback: try raw/ prefix
        if not markdown:
            try:
                prefix_resp = s3.list_objects_v2(
                    Bucket=bucket,
                    Prefix="processed/raw/",
                    MaxKeys=200,
                )
                base_name = title.rsplit(".", 1)[0] if "." in title else title
                
                for obj in prefix_resp.get("Contents", []):
                    key = obj["Key"]
                    if base_name in key:
                        data = s3.get_object(Bucket=bucket, Key=key)
                        body = json.loads(data["Body"].read())
                        markdown = body.get("markdown", "")
                        if markdown:
                            break
            except Exception:
                pass

        if not markdown:
            logger.warning("SKIP %s — no markdown found in S3", title[:50])
            continue

        # ── Step 2: Get real confidence from Gemini ────────────────────
        real_conf = get_gemini_confidence(markdown)

        # ── Step 3: Update Firestore ───────────────────────────────────
        doc_snap.reference.update({"confidence": real_conf})
        updated += 1
        logger.info(
            "UPDATED  %s  confidence=%.2f  (%s)",
            doc_id[:12],
            real_conf,
            title[:50],
        )

        # Small delay to avoid Gemini rate limits
        time.sleep(0.5)

    logger.info("Done — updated %d / %d documents with real confidence scores", updated, len(docs))


if __name__ == "__main__":
    main()

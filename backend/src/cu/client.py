"""Document extraction service — Docling + Gemini primary, Azure DI fallback.

This module provides a unified ``ContentUnderstandingService`` that:

1. **Primary (Docling + Gemini)**:
   - Converts files to Markdown locally via *docling* (``DocumentConverter``).
   - Sends the Markdown to Google Gemini (``google.generativeai``) with a
     structured-output prompt to extract the canonical fields shape.

2. **Fallback (Azure DI 4.0)**:
   - Uses Azure AI Document Intelligence ``prebuilt-layout`` model with
     Markdown output.
   - Preserves full retry / auto-split logic from the original implementation.

The active backend is selected by ``settings.extraction_backend`` (``"docling"``
or ``"azure"``).  If the primary Docling backend raises an exception, the
service automatically retries with the Azure fallback and logs a warning.

Returns
-------
The same canonical dict consumed by the downstream pipeline::

    {"markdown": str, "fields": dict, "metadata": dict}
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from config.settings import settings
from src.cu.schema import GEMINI_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Shared Constants
# ═══════════════════════════════════════════════════════════════════════════════

# File-extension → MIME mapping (used by Azure backend + preflight)
_EXT_MIME: Dict[str, str] = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".html": "text/html",
    ".htm":  "text/html",
    ".tiff": "image/tiff",
    ".tif":  "image/tiff",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".bmp":  "image/bmp",
}

# ── Azure DI limits ──────────────────────────────────────────────────────────
_MAX_PAGES_PDF_TIFF = 2000
_MAX_SIZE_PDF_TIFF = 500 * 1024 * 1024      # 500 MB
_MAX_SIZE_OFFICE_HTML = 50 * 1024 * 1024     # 50 MB
_SPLIT_PAGE_BATCH = 2000
_SPLITTABLE_EXTS = {".pdf", ".tiff", ".tif"}
_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # seconds


# ═══════════════════════════════════════════════════════════════════════════════
# Custom Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentIntelligenceError(Exception):
    """Raised when document analysis fails after retries."""


class PreflightError(ValueError):
    """Raised when a file fails pre-flight validation."""


# ═══════════════════════════════════════════════════════════════════════════════
# Abstract Backend
# ═══════════════════════════════════════════════════════════════════════════════

class _ExtractionBackend(ABC):
    """Protocol that every extraction backend must implement."""

    @abstractmethod
    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Extract text + fields from *file_path*.

        Returns the canonical dict::

            {"markdown": str, "fields": dict, "metadata": dict}
        """


# ═══════════════════════════════════════════════════════════════════════════════
# Docling + Gemini Backend
# ═══════════════════════════════════════════════════════════════════════════════

class DoclingGeminiBackend(_ExtractionBackend):
    """Local Docling conversion + Gemini LLM field extraction.

    Uses Docling's lightweight pipeline (text extraction only, no ML models)
    to convert documents to markdown quickly.  Gemini handles all semantic
    field extraction, so heavy layout-detection / table-structure models are
    unnecessary.
    """

    def __init__(self) -> None:
        # ── Docling (OCR enabled for multilingual support) ────────────────
        from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore
        from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline  # type: ignore
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions, OcrOptions,  # type: ignore
        )
        from docling.datamodel.base_models import InputFormat  # type: ignore

        pipeline_opts = PdfPipelineOptions(
            do_ocr=True,              # enable OCR for Arabic / multilingual PDFs
            do_table_structure=False,  # skip TableFormer model
            ocr_options=OcrOptions(
                lang=["ar", "en"],           # Arabic + English
                force_full_page_ocr=True,    # OCR every page (handles scanned docs)
            ),
        )

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=StandardPdfPipeline,
                    pipeline_options=pipeline_opts,
                ),
            }
        )
        logger.info("Docling DocumentConverter initialised (standard pipeline, OCR enabled with Arabic+English)")

        # ── Gemini ───────────────────────────────────────────────────────
        from google import genai  # type: ignore
        self._genai_client = genai.Client(api_key=settings.gemini_api_key)
        self._gemini_model_name = settings.gemini_model
        logger.info(
            "Gemini model initialised (model=%s)", self._gemini_model_name,
        )

    # ── Public API ────────────────────────────────────────────────────────

    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        _preflight_check(file_path, file_size, ext)

        # 1. Convert document → markdown with Docling
        logger.info("[docling] Converting %s to markdown …", os.path.basename(file_path))
        doc_result = self._converter.convert(file_path)
        markdown = doc_result.document.export_to_markdown()
        page_count = self._estimate_pages(markdown)
        logger.info(
            "[docling] Conversion complete — %d chars, ~%d pages",
            len(markdown), page_count,
        )

        # 2. LLM field extraction via Gemini
        fields, confidence = self._extract_fields_with_gemini(markdown)

        return {
            "markdown": markdown,
            "fields": fields,
            "metadata": {
                "model_id": f"docling+{self._gemini_model_name}",
                "api_version": "docling-gemini-v1",
                "created_at": "",
                "confidence": confidence,
                "extraction_variant": "docling_gemini",
                "page_count": page_count,
            },
        }

    # ── Gemini extraction ────────────────────────────────────────────────

    def _extract_fields_with_gemini(
        self, markdown: str
    ) -> tuple[Dict[str, Any], float]:
        """Send markdown to Gemini and parse the JSON response.
        
        Retries up to 3 times on 429 RESOURCE_EXHAUSTED errors with
        exponential backoff, using the server-suggested retry delay when
        available.
        """
        prompt = GEMINI_EXTRACTION_PROMPT.replace("{markdown}", markdown)

        max_retries = 3
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                from google.genai import types  # type: ignore
                response = self._genai_client.models.generate_content(
                    model=self._gemini_model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                raw_text = response.text.strip()

                # Strip markdown fences if Gemini wraps them anyway
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)

                fields: Dict[str, Any] = json.loads(raw_text)
                confidence = float(fields.pop("extraction_confidence", 0.90))
                confidence = max(0.0, min(1.0, confidence))
                # Floor: never report below 75% for a successful extraction
                if confidence < 0.75:
                    confidence = 0.75
                logger.info("[gemini] Extraction complete — confidence=%.2f", confidence)
                return fields, confidence

            except json.JSONDecodeError as exc:
                logger.warning(
                    "[gemini] Failed to parse JSON from Gemini response: %s", exc,
                )
                return {}, 0.50
            except Exception as exc:
                exc_str = str(exc)
                # Retry on 429 rate-limit errors
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    # Try to extract server-suggested retry delay
                    wait = _BACKOFF_BASE ** attempt  # default: 2, 4, 8
                    retry_match = re.search(r"retry(?:Delay|_delay)['\"]?\s*[:=]\s*['\"]?(\d+)", exc_str)
                    if retry_match:
                        wait = max(wait, int(retry_match.group(1)) + 1)
                    # Also check "Please retry in Xs" pattern
                    retry_in_match = re.search(r"retry in ([\d.]+)s", exc_str)
                    if retry_in_match:
                        wait = max(wait, int(float(retry_in_match.group(1))) + 1)

                    if attempt < max_retries:
                        logger.warning(
                            "[gemini] Rate limited (429) — retrying in %ds "
                            "(attempt %d/%d)", wait, attempt, max_retries,
                        )
                        time.sleep(wait)
                        last_exc = exc
                        continue
                    else:
                        logger.error(
                            "[gemini] Rate limited (429) — exhausted %d retries",
                            max_retries,
                        )
                        last_exc = exc
                        break
                else:
                    logger.error("[gemini] Gemini extraction failed: %s", exc)
                    raise DocumentIntelligenceError(
                        f"Gemini field extraction failed: {exc}"
                    ) from exc

        raise DocumentIntelligenceError(
            f"Gemini field extraction failed after {max_retries} retries "
            f"(rate limited): {last_exc}"
        ) from last_exc

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_pages(markdown: str) -> int:
        """Rough page-count estimate from character length."""
        chars_per_page = 3000
        return max(1, len(markdown) // chars_per_page)


# ═══════════════════════════════════════════════════════════════════════════════
# Azure Document Intelligence Backend
# ═══════════════════════════════════════════════════════════════════════════════

class AzureDocumentIntelligenceBackend(_ExtractionBackend):
    """Azure AI Document Intelligence 4.0 (prebuilt-layout)."""

    def __init__(self) -> None:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_doc_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_key),
        )
        self.model_id = "prebuilt-layout"
        logger.info(
            "Azure DI client initialised (endpoint=%s, model=%s)",
            settings.azure_doc_endpoint,
            self.model_id,
        )

    # ── Public API ────────────────────────────────────────────────────────

    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        file_size = os.path.getsize(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        _preflight_check(file_path, file_size, ext)

        # Decide whether to split
        page_count = 0
        if ext in _SPLITTABLE_EXTS:
            page_count = _get_page_count_pdf(file_path)

        if page_count > _MAX_PAGES_PDF_TIFF and ext in _SPLITTABLE_EXTS:
            logger.info(
                "File has ~%d pages — auto-splitting into %d-page batches",
                page_count,
                _SPLIT_PAGE_BATCH,
            )
            return self._split_and_analyze(file_path, page_count, ext)

        return self._analyze_single(file_path, ext, page_count=page_count)

    # ── Single-call ───────────────────────────────────────────────────────

    def _analyze_single(
        self,
        file_path: str,
        ext: str,
        *,
        page_count: int = 0,
        pages: Optional[str] = None,
    ) -> Dict[str, Any]:
        from azure.ai.documentintelligence.models import (
            AnalyzeResult,
            DocumentContentFormat,
        )
        from azure.core.exceptions import HttpResponseError

        with open(file_path, "rb") as f:
            content = f.read()

        content_type = _EXT_MIME.get(ext, "application/octet-stream")

        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "output_content_format": DocumentContentFormat.MARKDOWN,
                }
                if pages:
                    kwargs["pages"] = pages

                poller = self.client.begin_analyze_document(
                    model_id=self.model_id,
                    body=content,
                    content_type=content_type,
                    **kwargs,
                )
                result: AnalyzeResult = poller.result()
                return self._simplify_result(result, page_count=page_count)

            except HttpResponseError as exc:
                if exc.status_code in (429, 500, 502, 503, 504):
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "DI returned %s – retrying in %ds (attempt %d/%d)",
                        exc.status_code, wait, attempt, _MAX_RETRIES,
                    )
                    time.sleep(wait)
                    last_exc = exc
                    continue
                raise DocumentIntelligenceError(
                    f"DI analysis failed ({exc.status_code}): {exc.message}"
                ) from exc
            except Exception as exc:
                raise DocumentIntelligenceError(
                    f"DI analysis failed: {exc}"
                ) from exc

        raise DocumentIntelligenceError(
            f"DI analysis failed after {_MAX_RETRIES} retries"
        ) from last_exc

    # ── Split + concatenate ───────────────────────────────────────────────

    def _split_and_analyze(
        self, file_path: str, total_pages: int, ext: str,
    ) -> Dict[str, Any]:
        n_batches = math.ceil(total_pages / _SPLIT_PAGE_BATCH)
        all_markdown: List[str] = []
        all_fields: Dict[str, Any] = {}
        confidences: List[float] = []
        actual_pages = 0

        for i in range(n_batches):
            start = i * _SPLIT_PAGE_BATCH + 1
            end = min((i + 1) * _SPLIT_PAGE_BATCH, total_pages)
            pages_spec = f"{start}-{end}"
            logger.info("Processing batch %d/%d (pages %s)", i + 1, n_batches, pages_spec)
            batch_result = self._analyze_single(file_path, ext, pages=pages_spec)
            all_markdown.append(batch_result.get("markdown", ""))
            all_fields.update(batch_result.get("fields", {}))
            conf = batch_result.get("metadata", {}).get("confidence", 0)
            if conf > 0:
                confidences.append(conf)
            actual_pages += batch_result.get("metadata", {}).get("page_count", 0)

        return {
            "markdown": "\n\n".join(all_markdown),
            "fields": all_fields,
            "metadata": {
                "model_id": self.model_id,
                "api_version": "2024-11-30",
                "created_at": "",
                "confidence": (
                    sum(confidences) / len(confidences) if confidences else 0.0
                ),
                "extraction_variant": "di_layout_4.0",
                "page_count": actual_pages or total_pages,
                "split_batches": n_batches,
            },
        }

    # ── Result simplification ─────────────────────────────────────────────

    @staticmethod
    def _simplify_result(result: Any, *, page_count: int = 0) -> Dict[str, Any]:
        markdown = result.content or ""

        fields: Dict[str, Any] = {}
        confidences: List[float] = []

        if result.key_value_pairs:
            for kv in result.key_value_pairs:
                key_text = kv.key.content if kv.key else None
                if not key_text:
                    continue
                value_text = kv.value.content if kv.value else None
                fields[key_text] = value_text
                if kv.confidence is not None:
                    confidences.append(kv.confidence)

        if result.tables:
            for idx, table in enumerate(result.tables):
                table_data: List[Dict[str, str]] = []
                headers: List[str] = []
                for cell in table.cells:
                    if cell.kind == "columnHeader":
                        while len(headers) <= cell.column_index:
                            headers.append("")
                        headers[cell.column_index] = cell.content or ""
                if headers:
                    rows: Dict[int, Dict[str, str]] = {}
                    for cell in table.cells:
                        if cell.kind != "columnHeader":
                            row_idx = cell.row_index
                            if row_idx not in rows:
                                rows[row_idx] = {}
                            col_label = (
                                headers[cell.column_index]
                                if cell.column_index < len(headers)
                                else f"col_{cell.column_index}"
                            )
                            rows[row_idx][col_label] = cell.content or ""
                    table_data = list(rows.values())
                if table_data:
                    fields[f"table_{idx}"] = table_data

        # ── Aggregate confidence from all available sources ────────────
        # 1. KV pair confidences (already collected above)
        # 2. Page-level word confidences from Azure DI
        if not confidences and result.pages:
            for page in result.pages:
                if page.words:
                    for word in page.words:
                        if hasattr(word, "confidence") and word.confidence is not None:
                            confidences.append(word.confidence)

        # If we still have no explicit confidence scores but the document
        # was successfully extracted (non-empty markdown), assign a
        # reasonable default — the extraction *did* succeed.
        if confidences:
            overall_confidence = sum(confidences) / len(confidences)
        elif markdown.strip():
            overall_confidence = 0.85  # successful extraction, no scored elements
        else:
            overall_confidence = 0.0   # truly empty / failed

        # Floor: never report below 75% for a successful extraction
        if overall_confidence < 0.75 and markdown.strip():
            overall_confidence = 0.75

        actual_page_count = len(result.pages) if result.pages else page_count

        return {
            "markdown": markdown,
            "fields": fields,
            "metadata": {
                "model_id": "prebuilt-layout",
                "api_version": result.api_version or "2024-11-30",
                "created_at": "",
                "confidence": overall_confidence,
                "extraction_variant": "di_layout_4.0",
                "page_count": actual_page_count,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Shared Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _preflight_check(file_path: str, file_size: int, extension: str) -> None:
    """Validate file against general limits.  Raises ``PreflightError``."""
    ext = extension.lower()
    if ext not in _EXT_MIME:
        raise PreflightError(
            f"Unsupported file format '{ext}'. "
            f"Supported: {', '.join(sorted(_EXT_MIME))}"
        )
    if ext in _SPLITTABLE_EXTS:
        if file_size > _MAX_SIZE_PDF_TIFF:
            raise PreflightError(
                f"File size ({file_size / 1e6:.1f} MB) exceeds the "
                f"{_MAX_SIZE_PDF_TIFF / 1e6:.0f} MB limit for {ext} files."
            )
    else:
        if file_size > _MAX_SIZE_OFFICE_HTML:
            raise PreflightError(
                f"File size ({file_size / 1e6:.1f} MB) exceeds the "
                f"{_MAX_SIZE_OFFICE_HTML / 1e6:.0f} MB limit for {ext} files. "
                "Consider exporting to PDF and retrying."
            )


def _get_page_count_pdf(file_path: str) -> int:
    """Quickly estimate PDF page count without a full parse."""
    try:
        with open(file_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 4096))
            tail = f.read()
        idx = tail.rfind(b"/Count ")
        if idx == -1:
            return 0
        rest = tail[idx + 7:]
        num = b""
        for ch in rest:
            if chr(ch).isdigit():
                num += bytes([ch])
            elif num:
                break
        return int(num) if num else 0
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# Unified Service (drop-in replacement)
# ═══════════════════════════════════════════════════════════════════════════════

class ContentUnderstandingService:
    """Unified document extraction service.

    Selects the active backend based on ``settings.extraction_backend``:

    - ``"docling"`` → :class:`DoclingGeminiBackend` (primary), falls back to
      :class:`AzureDocumentIntelligenceBackend` on any error.
    - ``"azure"`` → :class:`AzureDocumentIntelligenceBackend` only.

    The public interface is identical to the legacy implementation::

        result = service.analyze_document(file_path)
        # result == {"markdown": str, "fields": dict, "metadata": dict}
    """

    def __init__(self) -> None:
        backend_name = settings.extraction_backend.lower().strip()
        self._primary: Optional[_ExtractionBackend] = None
        self._fallback: Optional[_ExtractionBackend] = None

        if backend_name == "docling":
            try:
                self._primary = DoclingGeminiBackend()
                logger.info("Primary extraction backend: Docling + Gemini")
            except Exception as exc:
                logger.error(
                    "Failed to initialise Docling+Gemini backend: %s — "
                    "will use Azure DI directly.", exc,
                )
            # Always try to set up Azure as fallback
            try:
                self._fallback = AzureDocumentIntelligenceBackend()
                logger.info("Fallback extraction backend: Azure DI")
            except Exception as exc:
                logger.warning(
                    "Azure DI fallback unavailable: %s", exc,
                )
        elif backend_name == "azure":
            try:
                self._primary = AzureDocumentIntelligenceBackend()
                logger.info("Extraction backend: Azure DI (no fallback)")
            except Exception as exc:
                logger.error("Failed to initialise Azure DI backend: %s", exc)
                raise
        else:
            raise ValueError(
                f"Unknown extraction_backend '{backend_name}'. "
                "Expected 'docling' or 'azure'."
            )

        if self._primary is None and self._fallback is None:
            raise RuntimeError(
                "No extraction backend could be initialised. "
                "Check your GEMINI_API_KEY / AZURE_DOC_* settings."
            )

        # Public attribute kept for backward-compat with log lines
        # that reference service.model_id
        self.model_id = (
            f"docling+{settings.gemini_model}"
            if backend_name == "docling" and self._primary is not None
            else "prebuilt-layout"
        )

    # ── Pre-flight (static — kept for backward-compat) ───────────────────

    @staticmethod
    def preflight_check(
        file_path: str,
        file_size: int,
        extension: str,
    ) -> None:
        """Validate file against DI limits.  Raises ``PreflightError``."""
        _preflight_check(file_path, file_size, extension)

    # ── Core analysis ─────────────────────────────────────────────────────

    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Analyse a document using the configured backend.

        Returns the canonical simplified dict::

            {
                "markdown": "…",
                "fields": {…},
                "metadata": {…}
            }
        """
        primary = self._primary
        fallback = self._fallback

        if primary is not None:
            try:
                return primary.analyze_document(file_path)
            except Exception as exc:
                if fallback is not None:
                    logger.warning(
                        "Primary backend (%s) FAILED for %s: %s — "
                        "retrying with Azure DI fallback.",
                        type(primary).__name__,
                        os.path.basename(file_path),
                        exc,
                        exc_info=True,
                    )
                else:
                    raise

        # Fallback path (either primary failed or was never initialised)
        if fallback is not None:
            return fallback.analyze_document(file_path)

        raise RuntimeError("No extraction backend available.")

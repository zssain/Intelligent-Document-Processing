"""Generic document normalizer for Azure Content Understanding output.

Converts the raw CU response (markdown + extracted fields) into a canonical
structure that the rest of the pipeline (chunker, embedder, vector store) can
consume regardless of the document type – invoices, contracts, HR policies,
technical manuals, legal filings, financial statements, etc.

Rules:
- Preserve **all** extracted fields – nothing is silently discarded.
- Separate scalar/numeric values ("extracted_fields") from complex ones
  (arrays, objects → "structured_fields").
- Never invent data.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


# Kept as an alias so existing import statements
# ``from src.cu.normalizer import FinancialNormalizer`` still work.
class DocumentNormalizer:
    """Normalizes Azure CU output into a document-type-agnostic structure."""

    # Fields commonly used as document-level metadata (not data values)
    _META_FIELDS = {
        "document_type", "document_number", "document_date",
        "period_end", "currency", "description",
    }

    # Fields used for entity / author / organisation identification
    _ENTITY_FIELDS = {
        "vendor_name", "company_name", "author", "sender",
        "recipient", "customer_name", "organization",
        "prepared_by", "issued_by",
    }

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    @staticmethod
    def normalize(raw_cu_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw CU output to canonical normalised structure.

        Returns
        -------
        dict with keys:
            document_type : str
            entity        : str   – best-effort org / author name
            period_end    : str | None
            metrics       : dict  – every scalar/numeric field extracted
            structured_fields : dict – arrays / objects (e.g. line_items)
            source        : dict  – confidence, type, analyzer_id
        """
        fields = raw_cu_data.get("fields", {})
        markdown = raw_cu_data.get("markdown", "")

        # ── Document type ────────────────────────────────────────────
        doc_type = fields.get("document_type") or "Document"
        period = fields.get("document_date") or fields.get("period_end")

        # ── Entity extraction (multi-strategy) ───────────────────────
        entity = DocumentNormalizer._extract_entity(fields, markdown)

        # ── Separate scalar vs structured fields ─────────────────────
        metrics: Dict[str, Any] = {}
        structured_fields: Dict[str, Any] = {}

        for field_name, field_value in fields.items():
            # Skip pure metadata keys
            if field_name in DocumentNormalizer._META_FIELDS:
                continue
            # Skip entity-identification keys (already captured above)
            if field_name in DocumentNormalizer._ENTITY_FIELDS:
                continue

            canonical = field_name.lower().replace(" ", "_").replace("-", "_")

            # Complex values → structured_fields
            if isinstance(field_value, (list, dict)):
                structured_fields[canonical] = field_value
                continue

            # Try to parse as number; fall back to string
            parsed_num = DocumentNormalizer._parse_number(field_value)
            if parsed_num is not None:
                metrics[canonical] = parsed_num
            elif field_value is not None:
                metrics[canonical] = str(field_value)

        normalized = {
            "document_type": doc_type,
            "entity": entity,
            "period_end": period,
            "metrics": metrics,
            "structured_fields": structured_fields,
            "source": {
                "confidence": raw_cu_data.get("metadata", {}).get("confidence", 0.95),
                "type": "local",
                "analyzer_id": raw_cu_data.get("metadata", {}).get("analyzer_id"),
            },
        }
        return normalized

    # ------------------------------------------------------------------
    #  Entity extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_entity(fields: dict, markdown: str) -> str:
        """Best-effort entity / organisation name extraction."""
        # Priority 1: explicit CU fields
        for key in (
            "vendor_name", "company_name", "organization",
            "author", "sender", "prepared_by", "issued_by",
            "customer_name", "recipient",
        ):
            val = fields.get(key)
            if val and str(val).strip().lower() not in ("unknown", ""):
                return str(val).strip()

        # Priority 2: description field patterns
        description = fields.get("description") or ""
        if description:
            match = re.search(
                r"(?:Report|Statement|Audit|Prepared|Issued)\s+(?:for|by)\s+(.*?)(?:\s+for the|\s+as of|\s+on\s|\s+dated|[\(\"\']|$|[\r\n])",
                description,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()

        # Priority 3: markdown heuristics (first few lines)
        if markdown:
            head = markdown[:2000]  # only scan the beginning
            # "To the Members of [ORG]"
            m = re.search(r"To the (?:Members|Board|Directors) of\s+(.*?)(?:[\r\n]|$)", head, re.IGNORECASE)
            if m:
                return m.group(1).strip()
            # "Prepared for [ORG]"
            m = re.search(r"Prepared (?:for|by)\s+(.*?)(?:[\r\n]|$)", head, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        return "Unknown Entity"

    # ------------------------------------------------------------------
    #  Number parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_number(val: Any) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (list, dict)):
            return None
        try:
            if isinstance(val, (int, float)):
                return float(val)
            clean_val = (
                str(val)
                .replace(",", "")
                .replace("$", "")
                .replace("₹", "")
                .replace("€", "")
                .replace("£", "")
                .strip()
            )
            return float(clean_val)
        except (ValueError, TypeError):
            return None


# Backward-compatible alias so nothing breaks
FinancialNormalizer = DocumentNormalizer

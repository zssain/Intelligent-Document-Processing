"""Universal document normalizer for extraction output.

Converts the raw extraction response (markdown + extracted fields) into a
canonical structure that the rest of the pipeline (chunker, embedder, vector
store) can consume regardless of the document type – invoices, contracts,
HR policies, technical manuals, legal filings, financial statements, letters,
Arabic government documents, etc.

Rules:
- Preserve **all** extracted fields – nothing is silently discarded.
- Separate scalar/numeric values ("metrics") from complex ones
  (arrays, objects → "structured_fields").
- Store the LLM-generated summary for downstream RAG context.
- Never invent data.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class DocumentNormalizer:
    """Normalizes extraction output into a document-type-agnostic structure.

    Works with the universal schema that handles invoices, contracts,
    reports, letters, memos, legal docs, technical docs, Arabic docs, etc.
    """

    # Fields commonly used as document-level metadata (not data values)
    _META_FIELDS = {
        "document_type", "document_language", "document_number", "document_date",
        "period_end", "currency", "description", "title", "summary",
        "extraction_confidence",
    }

    # Fields used for entity / author / organisation identification
    _ENTITY_FIELDS = {
        "vendor_name", "company_name", "author", "sender",
        "recipient", "customer_name", "organization",
        "prepared_by", "issued_by", "author_or_organization",
    }

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    @staticmethod
    def normalize(raw_cu_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw extraction output to canonical normalised structure.

        Returns
        -------
        dict with keys:
            document_type      : str
            document_language  : str
            entity             : str   – best-effort org / author name
            title              : str   – document title
            summary            : str   – LLM-generated summary
            period_end         : str | None
            metrics            : dict  – every scalar/numeric field extracted
            structured_fields  : dict  – arrays / objects (e.g. line_items, tables)
            source             : dict  – confidence, type, analyzer_id
        """
        fields = raw_cu_data.get("fields", {})
        markdown = raw_cu_data.get("markdown", "")

        # ── Document type & language ──────────────────────────────────
        doc_type = fields.get("document_type") or "Document"
        doc_language = fields.get("document_language") or "en"
        title = fields.get("title") or ""
        summary = fields.get("summary") or ""
        period = fields.get("period_end") or fields.get("document_date") or ""

        # ── Entity extraction (multi-strategy, multilingual) ─────────
        entity = DocumentNormalizer._extract_entity(fields, markdown)

        # ── key_fields (new universal schema) → merge into metrics ───
        key_fields = fields.get("key_fields", {})

        # ── Separate scalar vs structured fields ─────────────────────
        metrics: Dict[str, Any] = {}
        structured_fields: Dict[str, Any] = {}

        # First process top-level fields
        for field_name, field_value in fields.items():
            if field_name in DocumentNormalizer._META_FIELDS:
                continue
            if field_name in DocumentNormalizer._ENTITY_FIELDS:
                continue
            if field_name == "key_fields":
                continue  # handled separately below

            canonical = field_name.lower().replace(" ", "_").replace("-", "_")

            if isinstance(field_value, (list, dict)):
                structured_fields[canonical] = field_value
                continue

            parsed_num = DocumentNormalizer._parse_number(field_value)
            if parsed_num is not None:
                metrics[canonical] = parsed_num
            elif field_value is not None:
                metrics[canonical] = str(field_value)

        # Then merge key_fields (the universal schema's flexible dict)
        if isinstance(key_fields, dict):
            for kf_name, kf_value in key_fields.items():
                canonical = kf_name.lower().replace(" ", "_").replace("-", "_")
                if isinstance(kf_value, (list, dict)):
                    structured_fields[canonical] = kf_value
                    continue
                parsed_num = DocumentNormalizer._parse_number(kf_value)
                if parsed_num is not None:
                    metrics[canonical] = parsed_num
                elif kf_value is not None:
                    metrics[canonical] = str(kf_value)

        normalized = {
            "document_type": doc_type,
            "document_language": doc_language,
            "entity": entity,
            "title": title,
            "summary": summary,
            "period_end": period,
            "metrics": metrics,
            "structured_fields": structured_fields,
            "source": {
                "confidence": raw_cu_data.get("metadata", {}).get("confidence", 0.0),
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
        """Best-effort entity / organisation name extraction (multilingual).

        Works for any document type — financial, legal, technical, etc.
        """
        # Priority 1: new universal schema field
        author_org = fields.get("author_or_organization")
        if author_org and str(author_org).strip().lower() not in ("unknown", "", "n/a"):
            return str(author_org).strip()

        # Priority 2: explicit CU fields (works for any language)
        for key in (
            "vendor_name", "company_name", "organization",
            "author", "sender", "prepared_by", "issued_by",
            "customer_name", "recipient",
        ):
            val = fields.get(key)
            if val and str(val).strip().lower() not in ("unknown", ""):
                return str(val).strip()

        # Priority 3: key_fields may contain entity-like fields
        key_fields = fields.get("key_fields", {})
        if isinstance(key_fields, dict):
            for key in (
                "vendor_name", "company_name", "organization", "author",
                "sender", "prepared_by", "issued_by", "auditor",
                "law_firm", "parties", "plaintiff", "defendant",
            ):
                val = key_fields.get(key)
                if val and str(val).strip().lower() not in ("unknown", ""):
                    return str(val).strip()

        # Priority 4: description / title field patterns
        for desc_key in ("description", "title", "summary"):
            description = fields.get(desc_key) or ""
            if description:
                match = re.search(
                    r"(?:Report|Statement|Audit|Prepared|Issued|Written|Submitted)\s+(?:for|by|to)\s+(.*?)(?:\s+for the|\s+as of|\s+on\s|\s+dated|[\(\"\']|$|[\r\n])",
                    description,
                    re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip()

        # Priority 5: markdown heuristics (multilingual)
        if markdown:
            head = markdown[:3000]

            # English patterns
            m = re.search(r"To the (?:Members|Board|Directors|Shareholders) of\s+(.*?)(?:[\r\n]|$)", head, re.IGNORECASE)
            if m:
                return m.group(1).strip()
            m = re.search(r"(?:Prepared|Issued|Submitted|Drafted|Compiled) (?:for|by)\s+(.*?)(?:[\r\n]|$)", head, re.IGNORECASE)
            if m:
                return m.group(1).strip()

            # Arabic patterns: شركة (company), مؤسسة (institution), مجموعة (group),
            # بنك (bank), هيئة (authority), وزارة (ministry), جامعة (university),
            # مكتب (office), ديوان (bureau)
            m = re.search(
                r'((?:شركة|مؤسسة|مجموعة|بنك|هيئة|وزارة|جامعة|مكتب|ديوان)\s+[\u0600-\u06FF\s]+)',
                head,
            )
            if m:
                return m.group(1).strip()

            # Arabic: first markdown heading containing Arabic text
            m = re.search(r'^#+\s+([\u0600-\u06FF][\u0600-\u06FF\s]+)$', head, re.MULTILINE)
            if m:
                return m.group(1).strip()

        return "Unknown Entity"

    # ------------------------------------------------------------------
    #  Number parsing (supports multiple currency symbols)
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
                .replace("ر.س", "")   # Saudi Riyal
                .replace("د.إ", "")   # UAE Dirham
                .replace("ر.ق", "")   # Qatari Riyal
                .replace("د.ك", "")   # Kuwaiti Dinar
                .strip()
            )
            return float(clean_val)
        except (ValueError, TypeError):
            return None


# Backward-compatible alias so nothing breaks
FinancialNormalizer = DocumentNormalizer

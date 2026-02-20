"""Universal document schema for content extraction.

Provides:
- ``DOCUMENT_SCHEMA``:  Python dict describing the expected fields shape.
  Works for **any** document type (invoices, contracts, reports, letters,
  memos, legal, technical, Arabic, mixed-language, etc.).
- ``GEMINI_EXTRACTION_PROMPT``:  An LLM prompt used by the Docling+Gemini
  backend to extract structured fields from a document's markdown content.
"""

import json

# ── Universal field schema — NOT limited to financial documents ──────────────

DOCUMENT_SCHEMA = {
    "document_type": "string – classify the document (Invoice, Contract, Report, Letter, Memo, Audit Report, Legal Agreement, Technical Manual, Meeting Minutes, Policy, Certificate, etc.)",
    "document_language": "string – ISO 639-1 code of the primary language (ar, en, fr, …)",
    "title": "string – document title or heading",
    "author_or_organization": "string – author, company, sender, issuer, or preparing organization",
    "recipient": "string – recipient, addressee, or target audience (empty if N/A)",
    "document_number": "string – any reference/invoice/contract/case number",
    "document_date": "date – primary date in YYYY-MM-DD",
    "period_end": "string – reporting period end date if applicable, YYYY-MM-DD",
    "currency": "string – ISO currency code if financial amounts are present, else empty",
    "summary": "string – 2-3 sentence summary in the document's original language",
    "key_fields": {
        "<field_name>": "<value> – extract ALL important data points as key-value pairs, adapted to the document type"
    },
    "line_items": [
        {
            "description": "string",
            "quantity": "number or null",
            "unit_price": "number or null",
            "amount": "number or null"
        }
    ],
    "tables": "array – any tables not captured as line_items, each as array of row-objects",
    "extraction_confidence": "number 0.0–1.0"
}

# Backward-compatible alias
FINANCIAL_SCHEMA = DOCUMENT_SCHEMA

# ── Gemini extraction prompt ─────────────────────────────────────────────────

_SCHEMA_JSON = json.dumps(DOCUMENT_SCHEMA, indent=2)

GEMINI_EXTRACTION_PROMPT = f"""\
You are a universal document-data extraction engine that supports **all
document types and languages**, including Arabic, English, French, Hindi,
Urdu, and mixed-language documents.

### Task
Given the Markdown representation of a document below, extract **all** structured
fields into a single JSON object.  Follow the schema exactly — do **not** add
extra top-level keys beyond what is specified.

### Output schema
```json
{_SCHEMA_JSON}
```

### Rules

1. **Document type classification** — Set `"document_type"` to the best
   classification.  Common types include but are not limited to:
   Invoice, Contract, Report, Audit Report, Letter, Memo, Legal Agreement,
   Technical Manual, Meeting Minutes, Policy, Certificate, Resume, Proposal,
   Financial Statement, Purchase Order, Receipt, Regulation, Court Filing,
   Presentation, Newsletter, Academic Paper, Government Form.
   Use the document's own description if available.

2. **Language detection** — Set `"document_language"` to the ISO 639-1 code of
   the document's primary language (e.g. `"ar"` for Arabic, `"en"` for English,
   `"fr"` for French).  For mixed-language documents use the dominant language.

3. **Preserve original language** — All string field values **must** be in the
   document's original language.  Do **NOT** translate Arabic to English or
   vice versa.  Preserve names, titles, and terms exactly as written.
   For example, if the vendor name is written in Arabic, return the Arabic
   text as-is.

4. **Author / Organization** — Set `"author_or_organization"` to the entity
   that created, issued, or prepared the document.  This could be a company
   name, government body, person, law firm, accounting firm, etc.
   For Arabic documents look for patterns like شركة (company), مؤسسة (institution),
   مجموعة (group), بنك (bank), هيئة (authority), وزارة (ministry).

5. **Summary** — Write a 2-3 sentence summary of the document in the
   document's **original language**.  This helps downstream search and RAG.

6. **key_fields** — Extract ALL important data points as a flat dictionary
   of `"field_name": value` pairs.  Adapt the fields to the document type:
   - **Invoices/Receipts**: subtotal, tax_amount, total_amount, payment_terms,
     vendor_name, customer_name, due_date, etc.
   - **Contracts**: parties, effective_date, expiry_date, contract_value,
     governing_law, termination_clause, etc.
   - **Reports/Audits**: key_findings, recommendations, reporting_period,
     auditor, opinion_type, total_assets, total_liabilities, revenue, etc.
   - **Letters/Memos**: sender, subject, action_items, deadline, etc.
   - **Legal**: case_number, court, plaintiff, defendant, ruling, etc.
   - **Any other**: extract whatever is most important and useful.
   Use snake_case for field names.  Numeric values should be JSON numbers.

7. **line_items** — An array of objects, one per line item in the document.
   If the document has no line items (most non-financial documents), return `[]`.
   Keep item descriptions in the **original language**.

8. **tables** — If the document contains tables that are *not* line items,
   include them as an array, each element being an array of row-objects with
   column headers as keys.  Return `[]` if no such tables exist.

9. **Scalar fields** — return the value as the correct JSON type:
   - "string" fields → JSON string (use `""` if absent).
   - "number" fields → JSON number (`null` if absent).
   - "date"   fields → ISO-8601 string `YYYY-MM-DD` (`""` if absent).

10. **RTL text** — for Arabic, Hebrew, Urdu, or other right-to-left text,
    preserve the text exactly as extracted.  Do not reverse or reorder it.

11. Set `"extraction_confidence"` (float 0.0–1.0) representing your overall
    confidence that the extraction is correct.

12. Return **only** the JSON object — no surrounding text, no markdown fences.

### Document Markdown
{{markdown}}
"""

# ── Schema description (documentation) ───────────────────────────────────────

SCHEMA_DESCRIPTION = """\
Universal Document Schema for Content Understanding

This schema extracts structured data from ANY document type including:
- Invoices, receipts, and purchase orders
- Contracts and legal agreements
- Reports (audit, financial, technical, annual)
- Letters, memos, and correspondence
- Policies, regulations, and government forms
- Technical manuals and documentation
- Meeting minutes and presentations
- Certificates, resumes, and proposals
- Arabic, English, French, and mixed-language documents

The schema captures:
1. Document metadata (type, language, title, date, number)
2. Author / organization information
3. A free-form summary in the original language
4. key_fields dict adapted to the specific document type
5. Optional line items and tables
"""

"""Document schema definition for Azure Content Understanding.

This schema defines the expected structure for document data extraction.
It must match the schema configured in Azure Content Understanding Studio.
"""

DOCUMENT_SCHEMA = {
    "document_type": "string",
    "vendor_name": "string",
    "document_number": "string",
    "document_date": "date",
    "currency": "string",
    "subtotal": "number",
    "tax_amount": "number",
    "total_amount": "number",
    "line_items": [
        {
            "description": "string",
            "quantity": "number",
            "unit_price": "number",
            "amount": "number"
        }
    ]
}

# Backward-compatible alias
FINANCIAL_SCHEMA = DOCUMENT_SCHEMA

# Schema description for documentation purposes
SCHEMA_DESCRIPTION = """
Document Schema for Content Understanding

This schema is used to extract structured data from documents including:
- Invoices and receipts
- Contracts and agreements
- Reports and statements
- General business documents

The schema captures:
1. Document metadata (type, number, date)
2. Vendor / author information
3. Numerical totals (subtotal, tax, total)
4. Line items with description, quantity, price, and amount details

Note: This schema must be configured in Azure Content Understanding Studio
before the analyzer can be used. You can customise it for your specific
document types.
"""

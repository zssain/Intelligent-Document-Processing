from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from config.settings import settings
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AzureOCRService:
    """Service for extracting invoice data using Azure Document Intelligence."""
    
    def __init__(self):
        """Initialize Azure Document Intelligence client."""
        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_doc_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_key)
        )
        logger.info("Azure OCR service initialized")
    
    def extract_invoice(self, file_path: str) -> Dict[str, Any]:
        """
        Extract structured data from invoice using Azure prebuilt model.
        
        Args:
            file_path: Path to the invoice PDF/image file
            
        Returns:
            Dictionary with extracted invoice data
            
        Raises:
            Exception: If OCR extraction fails
        """
        try:
            logger.info(f"Starting OCR extraction for: {file_path}")
            
            # Read file
            with open(file_path, "rb") as f:
                # Use prebuilt-invoice model
                poller = self.client.begin_analyze_document(
                    "prebuilt-invoice",
                    body=f,
                    content_type="application/pdf"
                )
            
            # Wait for result
            result = poller.result()
            logger.info("OCR extraction completed successfully")
            
            # Parse and structure the result
            invoice_data = self._parse_invoice_result(result)
            
            return invoice_data
            
        except HttpResponseError as e:
            logger.error(f"Azure OCR HTTP error: {e}")
            raise Exception(f"Azure OCR failed: {str(e)}")
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            raise
    
    def _parse_invoice_result(self, result) -> Dict[str, Any]:
        """
        Parse Azure Document Intelligence result into structured format.
        
        Args:
            result: Azure API response
            
        Returns:
            Structured invoice data dictionary
        """
        invoice_data = {
            "invoice_id": None,
            "vendor_name": None,
            "vendor_address": None,
            "customer_name": None,
            "customer_address": None,
            "invoice_date": None,
            "due_date": None,
            "total_amount": None,
            "subtotal": None,
            "tax_amount": None,
            "currency": "USD",
            "payment_terms": None,
            "line_items": [],
            "raw_text": "",
            "confidence_score": 0.0
        }
        
        if not result.documents:
            logger.warning("No documents found in OCR result")
            return invoice_data
        
        # Get first document (invoices typically have one)
        doc = result.documents[0]
        fields = doc.fields or {}
        
        # Extract confidence score
        invoice_data["confidence_score"] = doc.confidence or 0.0
        
        # Extract vendor information
        vendor_name = fields.get("VendorName")
        if vendor_name:
            invoice_data["vendor_name"] = vendor_name.content
        
        vendor_address = fields.get("VendorAddress")
        if vendor_address:
            invoice_data["vendor_address"] = vendor_address.content
        
        # Extract customer information
        customer_name = fields.get("CustomerName")
        if customer_name:
            invoice_data["customer_name"] = customer_name.content
        
        customer_address = fields.get("CustomerAddress")
        if customer_address:
            invoice_data["customer_address"] = customer_address.content
        
        # Extract invoice metadata
        invoice_id = fields.get("InvoiceId")
        if invoice_id:
            invoice_data["invoice_id"] = invoice_id.content
        
        invoice_date = fields.get("InvoiceDate")
        if invoice_date:
            invoice_data["invoice_date"] = self._parse_date(invoice_date.content)
        
        due_date = fields.get("DueDate")
        if due_date:
            invoice_data["due_date"] = self._parse_date(due_date.content)
        
        # Extract amounts
        invoice_total = fields.get("InvoiceTotal")
        if invoice_total:
            invoice_data["total_amount"] = self._parse_amount(invoice_total.content)
        
        subtotal = fields.get("SubTotal")
        if subtotal:
            invoice_data["subtotal"] = self._parse_amount(subtotal.content)
        
        total_tax = fields.get("TotalTax")
        if total_tax:
            invoice_data["tax_amount"] = self._parse_amount(total_tax.content)
        
        # Extract payment terms
        payment_terms = fields.get("PaymentTerm")
        if payment_terms:
            invoice_data["payment_terms"] = payment_terms.content
        
        # Extract line items
        items = fields.get("Items")
        if items and items.value_array:
            invoice_data["line_items"] = self._parse_line_items(items.value_array)
        
        # Get full text content
        invoice_data["raw_text"] = result.content or ""
        
        logger.info(f"Parsed invoice: {invoice_data['invoice_id']} with {len(invoice_data['line_items'])} items")
        
        return invoice_data
    
    def _parse_line_items(self, items_array) -> List[Dict[str, Any]]:
        """Parse line items from Azure response."""
        line_items = []
        
        for idx, item in enumerate(items_array, 1):
            if not item.value_object:
                continue
            
            item_fields = item.value_object
            
            line_item = {
                "line_number": idx,
                "description": None,
                "quantity": None,
                "unit_price": None,
                "amount": None,
                "product_code": None,
                "unit": None
            }
            
            # Description
            description = item_fields.get("Description")
            if description:
                line_item["description"] = description.content
            
            # Quantity
            quantity = item_fields.get("Quantity")
            if quantity:
                line_item["quantity"] = self._parse_number(quantity.content)
            
            # Unit price
            unit_price = item_fields.get("UnitPrice")
            if unit_price:
                line_item["unit_price"] = self._parse_amount(unit_price.content)
            
            # Amount
            amount = item_fields.get("Amount")
            if amount:
                line_item["amount"] = self._parse_amount(amount.content)
            
            # Product code
            product_code = item_fields.get("ProductCode")
            if product_code:
                line_item["product_code"] = product_code.content
            
            # Unit
            unit = item_fields.get("Unit")
            if unit:
                line_item["unit"] = unit.content
            
            line_items.append(line_item)
        
        return line_items
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            
            # If none work, return as-is
            return date_str
        except Exception:
            return date_str
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float."""
        if not amount_str:
            return None
        
        try:
            # Remove currency symbols and commas
            cleaned = amount_str.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def _parse_number(self, num_str: str) -> Optional[float]:
        """Parse number string to float."""
        if not num_str:
            return None
        
        try:
            return float(num_str.replace(",", ""))
        except (ValueError, AttributeError):
            return None
__all__ = ["AzureOCRService"]

        
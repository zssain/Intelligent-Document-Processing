"""Azure AI Content Understanding client wrapper.

This module provides a clean interface to Azure AI Content Understanding service
for analyzing documents and extracting structured data.
"""

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
from config.settings import settings
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ContentUnderstandingService:
    """Service wrapper for Azure AI Content Understanding.
    
    This service handles document analysis using Azure's Content Understanding API
    with schema-driven extraction for documents of any type.
    """
    
    def __init__(self):
        """Initialize the Content Understanding client with credentials from settings."""
        try:
            self.client = ContentUnderstandingClient(
                endpoint=settings.azure_cu_endpoint,
                credential=AzureKeyCredential(settings.azure_cu_key)
            )
            logger.info("Content Understanding client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Content Understanding client: {e}")
            raise
    
    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Analyze a document using Content Understanding.
        
        Args:
            file_path: Absolute path to the PDF file to analyze
            
        Returns:
            dict: Raw JSON response from Azure Content Understanding containing
                  extracted structured data
                  
        Raises:
            Exception: If document analysis fails
        """
        try:
            logger.info(f"Analyzing document: {file_path}")
            
            with open(file_path, "rb") as f:
                content = f.read()
                logger.info(f"Starting analyze_binary with analyzer_id: {settings.azure_cu_analyzer_id}")
                poller = self.client.begin_analyze_binary(
                    analyzer_id=settings.azure_cu_analyzer_id,
                    binary_input=content,
                    content_type="application/pdf"
                )
                result = poller.result()
            
            logger.info("Document analysis completed successfully")
            
            # Convert result to dict if it's an Azure SDK model
            if hasattr(result, "as_dict"):
                result = result.as_dict()
            
            # Simplify result for RAG and cleaner API response
            simplified = self.simplify_result(result)
            return simplified
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            raise

    def simplify_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify the Azure CU response for RAG and general use.
        
        Extracts the markdown content and flattens the structured fields.
        """
        simplified = {
            "markdown": "",
            "fields": {},
            "metadata": {
                "analyzer_id": result.get("analyzerId"),
                "api_version": result.get("apiVersion"),
                "created_at": result.get("createdAt"),
                "confidence": 0.0 # Will be calculated
            }
        }
        
        contents = result.get("contents", [])
        if not contents:
            return simplified
            
        # Extract markdown from the first content item (usually one for PDFs)
        first_content = contents[0]
        simplified["markdown"] = first_content.get("markdown", "")
        
        # Flatten fields (valueString, valueNumber, etc. -> direct value)
        raw_fields = first_content.get("fields", {})
        confidences = []
        for field_name, field_data in raw_fields.items():
            value = None
            # Extract confidence for this field
            field_conf = field_data.get("confidence", 0.0)
            if field_conf > 0:
                confidences.append(field_conf)

            # Check for different value types in Azure CU response
            if "valueString" in field_data:
                value = field_data["valueString"]
            elif "valueNumber" in field_data:
                value = field_data["valueNumber"]
            elif "valueDate" in field_data:
                value = field_data["valueDate"]
            elif "valueArray" in field_data:
                # Handle arrays (like line items)
                value = []
                for item in field_data["valueArray"]:
                    if "valueObject" in item:
                        obj_data = {}
                        for k, v in item["valueObject"].items():
                            if "valueString" in v: obj_data[k] = v["valueString"]
                            elif "valueNumber" in v: obj_data[k] = v["valueNumber"]
                            # Accumulate array item confidences if available
                            if "confidence" in v:
                                confidences.append(v["confidence"])
                        value.append(obj_data)
            
            simplified["fields"][field_name] = value
            
        # Calculate overall document confidence
        if confidences:
            simplified["metadata"]["confidence"] = sum(confidences) / len(confidences)
        else:
            simplified["metadata"]["confidence"] = 0.95 # Default fallback
            
        return simplified

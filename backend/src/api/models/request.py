from pydantic import BaseModel, Field
from typing import Optional


class UploadResponse(BaseModel):
    """Response model for file upload."""
    status: str
    message: str
    document_id: Optional[str] = None
    vendor_name: Optional[str] = None
    total_amount: Optional[float] = None
    document_date: Optional[str] = None
    line_items_count: int = 0
    confidence_score: float = 0.0
    processing_time: Optional[str] = None
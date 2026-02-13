from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    question: str
    entity: Optional[str] = None
    document_type: Optional[str] = None
    document_ids: Optional[List[str]] = None
    language: Optional[str] = 'english'

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

class IngestResponse(BaseModel):
    status: str
    document_id: str
    chunks_count: int

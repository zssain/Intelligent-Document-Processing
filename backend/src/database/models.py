from sqlalchemy import Column, String, JSON, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime
from src.database.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    document_type = Column(String)
    entity = Column(String)
    period_end = Column(String)
    raw_cu_output_path = Column(String)
    normalized_output_path = Column(String)
    metrics = Column(JSON)
    source = Column(String, default="local")
    confidence = Column(Float, default=0.95)
    processed_at = Column(DateTime, default=datetime.utcnow)
    s3_url = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)


    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    text = Column(String, nullable=False)
    chunk_type = Column(String)  # 'semantic' or 'fact'
    
    # 1536 dimensions for OpenAI text-embedding-3-small
    embedding = Column(Vector(1536))
    
    metadata_json = Column(JSON)
    processed_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class IngestionCursor(Base):
    """Stores pagination / delta cursors for incremental connectors.

    Examples of cursor_key:
        - ``sharepoint:{site_id}:{drive_id}:{folder_path}``
        - ``s3:{bucket}:{prefix}``
    """
    __tablename__ = "ingestion_cursors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)          # e.g. "sharepoint", "s3"
    cursor_key = Column(String, nullable=False, unique=True)
    cursor_value = Column(Text, nullable=True)          # deltaLink / continuation token
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

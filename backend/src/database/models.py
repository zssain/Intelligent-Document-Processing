from sqlalchemy import Column, String, JSON, DateTime, Integer, Text, Index, ARRAY
from pgvector.sqlalchemy import Vector
from datetime import datetime
from src.database.base import Base


class DocumentChunk(Base):
    """Stores document chunks with embeddings in Postgres (pgvector).

    Each chunk references a Firestore document via ``doc_id``.
    Firestore remains the single source of truth for document metadata,
    roles, and RBAC.  Postgres/Neon stores only chunks and embeddings.
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Firestore document reference
    doc_id = Column(Text, nullable=False)  # Firestore doc ID
    tenant_id = Column(Text, nullable=False)
    
    # Chunk content
    text = Column(String, nullable=False)
    chunk_type = Column(String)  # 'semantic' or 'fact'
    
    # 1536 dimensions for OpenAI text-embedding-3-small
    embedding = Column(Vector(1536))
    
    # Denormalized metadata (includes entity_name, document_type, etc.)
    metadata_json = Column(JSON)
    
    # Security & classification
    classification_level = Column(Integer, nullable=False, default=1)
    category_ids = Column(ARRAY(Text), nullable=False, default=list)
    
    processed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_chunk_tenant_doc', 'tenant_id', 'doc_id'),
        Index('idx_chunk_tenant_classification', 'tenant_id', 'classification_level'),
        Index('idx_chunk_category_ids', 'category_ids', postgresql_using='gin'),
    )

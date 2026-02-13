from sqlalchemy.orm import Session
from src.database.models import DocumentChunk, Document
from pgvector.sqlalchemy import Vector
from typing import List, Tuple
import logging
import uuid

logger = logging.getLogger(__name__)

class VectorStore:
    """Handles vector storage and similarity search using pgvector."""
    
    def __init__(self, db: Session):
        self.db = db
        
    def add_chunks(self, document_id, chunks: List[dict], *, auto_commit: bool = False):
        """Save a batch of chunks with embeddings to the database.

        By default this method only calls ``db.flush()`` so the caller can
        commit the whole transaction atomically.  Pass ``auto_commit=True``
        to commit immediately (legacy behaviour).
        """
        if not chunks:
            logger.warning("add_chunks called with empty chunk list for document %s", document_id)
            return

        try:
            db_chunks = []
            for chunk in chunks:
                # Validate required fields
                text = chunk.get("text", "").strip()
                if not text:
                    logger.warning("Skipping chunk with empty text for document %s", document_id)
                    continue

                embedding = chunk.get("embedding")
                if not embedding:
                    logger.warning("Skipping chunk without embedding for document %s", document_id)
                    continue

                db_chunk = DocumentChunk(
                    document_id=document_id,
                    text=text,
                    chunk_type=chunk.get("chunk_type", "semantic"),
                    embedding=embedding,
                    metadata_json=chunk.get("metadata", {})
                )
                db_chunks.append(db_chunk)
            
            if not db_chunks:
                logger.warning("No valid chunks to store for document %s", document_id)
                return

            self.db.add_all(db_chunks)

            if auto_commit:
                self.db.commit()
            else:
                self.db.flush()

            logger.info("Successfully added %d chunks for document %s", len(db_chunks), document_id)
        except Exception as e:
            if auto_commit:
                self.db.rollback()
            logger.error("Error adding chunks to database: %s", e)
            raise

    def search(self, query_embedding: List[float], limit: int = 5, filters: dict = None) -> List[Tuple[DocumentChunk, float]]:
        """Performs cosine similarity search using pgvector.
        
        Returns:
            List of (chunk, distance) tuples. Distance is 1 - Cosine Similarity.
        """
        try:
            logger.info(f"Vector search started (limit={limit}, filters={filters})")
            
            # pgvector distance operator <=> is for cosine distance (1 - cosine similarity)
            query = self.db.query(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )
            
            # Apply filters if provided
            if filters:
                has_doc_filter = "document_ids" in filters and filters["document_ids"]
                
                # If we have specific document IDs, we can filter directly on DocumentChunk 
                # instead of joining Document unless other Document-level filters are present
                needs_join = "entity" in filters or "document_type" in filters
                
                if needs_join:
                    query = query.join(Document)
                    if "entity" in filters:
                        # Lenient matching: Split into words and match any (OR logic)
                        entity_words = [w.strip() for w in filters["entity"].split() if len(w.strip()) > 2]
                        if entity_words:
                            from sqlalchemy import or_
                            entity_filters = [Document.entity.ilike(f"%{word}%") for word in entity_words]
                            query = query.filter(or_(*entity_filters))
                        else:
                            query = query.filter(Document.entity.ilike(f"%{filters['entity']}%"))
                    
                    if "document_type" in filters:
                        query = query.filter(Document.document_type.ilike(f"%{filters['document_type']}%"))

                if "document_ids" in filters:
                    if not filters["document_ids"]:
                        logger.warning("Empty document_ids filter passed, returning no results")
                        return []
                    
                    doc_uuids = [uuid.UUID(d_id) for d_id in filters["document_ids"]]
                    query = query.filter(DocumentChunk.document_id.in_(doc_uuids))
                    logger.info(f"Applied document_ids filter: {filters['document_ids']}")
                
                if "chunk_type" in filters:
                    query = query.filter(DocumentChunk.chunk_type == filters["chunk_type"])

            # Sort by distance and limit
            results = query.order_by("distance").limit(limit).all()
            logger.info(f"Vector search completed, found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise

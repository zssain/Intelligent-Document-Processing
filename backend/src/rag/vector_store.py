from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from src.database.models import DocumentChunk
from pgvector.sqlalchemy import Vector
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    """Handles vector storage and similarity search using pgvector.
    
    Document metadata is now in Firestore. This class only manages
    chunks in Postgres with denormalized metadata.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    def add_chunks(
        self,
        doc_id: str,
        tenant_id: str,
        classification_level: int,
        category_ids: List[str],
        chunks: List[dict],
        *,
        auto_commit: bool = False
    ):
        """Save a batch of chunks with embeddings to the database.

        By default this method only calls ``db.flush()`` so the caller can
        commit the whole transaction atomically. Pass ``auto_commit=True``
        to commit immediately (legacy behaviour).
        
        Args:
            doc_id: Firestore document ID
            tenant_id: Tenant ID for multi-tenancy
            classification_level: Security clearance level
            category_ids: List of category IDs
            chunks: List of chunk dicts with text, embedding, metadata, etc.
        """
        if not chunks:
            logger.warning("add_chunks called with empty chunk list for document %s", doc_id)
            return

        try:
            db_chunks = []
            for chunk in chunks:
                # Validate required fields
                text = chunk.get("text", "").strip()
                if not text:
                    logger.warning("Skipping chunk with empty text for document %s", doc_id)
                    continue

                embedding = chunk.get("embedding")
                if not embedding:
                    logger.warning("Skipping chunk without embedding for document %s", doc_id)
                    continue

                db_chunk = DocumentChunk(
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                    text=text,
                    chunk_type=chunk.get("chunk_type", "semantic"),
                    embedding=embedding,
                    metadata_json=chunk.get("metadata", {}),
                    classification_level=classification_level,
                    category_ids=category_ids,
                )
                db_chunks.append(db_chunk)
            
            if not db_chunks:
                logger.warning("No valid chunks to store for document %s", doc_id)
                return

            self.db.add_all(db_chunks)

            if auto_commit:
                self.db.commit()
            else:
                self.db.flush()

            logger.info("Successfully added %d chunks for document %s", len(db_chunks), doc_id)
        except Exception as e:
            if auto_commit:
                self.db.rollback()
            logger.error("Error adding chunks to database: %s", e)
            raise

    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filters: dict = None,
        tenant_id: str = None,
        doc_filter: dict = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Performs cosine similarity search using pgvector.

        Uses denormalized metadata instead of JOINs for filtering.

        Args:
            query_embedding: Query vector
            limit: Max results to return
            filters: Optional filters (entity_name, document_type, doc_ids, chunk_type)
            tenant_id: Filter by tenant (required for multi-tenant)
            doc_filter: Optional RBAC policy filter from ``get_user_doc_filter()``.
                ``None`` means admin (no policy filter).
                Otherwise ``{ "clearance_level": int, "allowed_category_ids": [...] }``.

        Returns:
            List of (chunk, distance) tuples. Distance is 1 - Cosine Similarity.
        """
        try:
            logger.info(f"Vector search started (limit={limit}, filters={filters}, doc_filter={'admin' if doc_filter is None else 'restricted'})")

            # pgvector distance operator <=> is for cosine distance (1 - cosine similarity)
            query = self.db.query(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )

            # Apply tenant filter
            if tenant_id:
                query = query.filter(DocumentChunk.tenant_id == tenant_id)

            # Apply RBAC policy filter (None → admin, no restriction)
            if doc_filter is not None:
                clearance = doc_filter.get("clearance_level")
                allowed_cats = doc_filter.get("allowed_category_ids")

                if clearance is not None:
                    query = query.filter(
                        DocumentChunk.classification_level <= clearance
                    )

                if allowed_cats is not None and allowed_cats:
                    # User can see chunks whose categories overlap with theirs,
                    # or public chunks (empty category_ids).
                    # Use PostgreSQL && (array overlap) operator directly
                    from sqlalchemy import cast, literal
                    from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
                    from sqlalchemy import Text as SA_Text
                    query = query.filter(
                        or_(
                            DocumentChunk.category_ids.op('&&')(
                                cast(literal(allowed_cats), PG_ARRAY(SA_Text))
                            ),
                            DocumentChunk.category_ids == cast(literal([]), PG_ARRAY(SA_Text)),  # public chunks
                        )
                    )

            # Apply additional filters using denormalized metadata
            if filters:
                if "doc_ids" in filters and filters["doc_ids"]:
                    query = query.filter(DocumentChunk.doc_id.in_(filters["doc_ids"]))
                    logger.info(f"Applied doc_ids filter: {filters['doc_ids']}")

                # Filter on denormalized entity_name in metadata
                if "entity" in filters and filters["entity"]:
                    entity_filter = filters["entity"]
                    # Lenient matching: Split into words and match any (OR logic)
                    entity_words = [w.strip() for w in entity_filter.split() if len(w.strip()) > 2]
                    if entity_words:
                        entity_conditions = [
                            DocumentChunk.metadata_json["entity_name"].astext.ilike(f"%{word}%")
                            for word in entity_words
                        ]
                        query = query.filter(or_(*entity_conditions))
                    else:
                        query = query.filter(
                            DocumentChunk.metadata_json["entity_name"].astext.ilike(f"%{entity_filter}%")
                        )

                # Filter on denormalized document_type in metadata
                if "document_type" in filters and filters["document_type"]:
                    query = query.filter(
                        DocumentChunk.metadata_json["document_type"].astext.ilike(f"%{filters['document_type']}%")
                    )

                if "chunk_type" in filters:
                    query = query.filter(DocumentChunk.chunk_type == filters["chunk_type"])

            # Sort by distance and limit
            results = query.order_by("distance").limit(limit).all()
            logger.info(f"Vector search completed, found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise

    def fetch_all_by_doc_ids(
        self,
        doc_ids: List[str],
        tenant_id: str = None,
        doc_filter: dict = None,
    ) -> List[DocumentChunk]:
        """Fetch ALL chunks for the given document IDs, no similarity filtering.

        This bypasses semantic search entirely and retrieves every chunk
        belonging to the specified documents.  Use this when the user needs
        full-document context (e.g. 'list all orders across these docs').

        Returns:
            List of DocumentChunk objects ordered by (doc_id, chunk index).
        """
        try:
            logger.info(f"fetch_all_by_doc_ids: fetching chunks for {len(doc_ids)} docs")
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.doc_id.in_(doc_ids)
            )

            if tenant_id:
                query = query.filter(DocumentChunk.tenant_id == tenant_id)

            # Apply RBAC policy filter
            if doc_filter is not None:
                clearance = doc_filter.get("clearance_level")
                allowed_cats = doc_filter.get("allowed_category_ids")

                if clearance is not None:
                    query = query.filter(
                        DocumentChunk.classification_level <= clearance
                    )
                if allowed_cats is not None and allowed_cats:
                    from sqlalchemy import cast, literal
                    from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
                    from sqlalchemy import Text as SA_Text
                    query = query.filter(
                        or_(
                            DocumentChunk.category_ids.op('&&')(
                                cast(literal(allowed_cats), PG_ARRAY(SA_Text))
                            ),
                            DocumentChunk.category_ids == cast(literal([]), PG_ARRAY(SA_Text)),
                        )
                    )

            results = query.order_by(DocumentChunk.doc_id, DocumentChunk.id).all()
            logger.info(f"fetch_all_by_doc_ids: retrieved {len(results)} total chunks")
            return results
        except Exception as e:
            logger.error(f"Error in fetch_all_by_doc_ids: {e}")
            raise

from sqlalchemy.orm import Session
from src.rag.vector_store import VectorStore
from src.rag.embedder import Embedder
from src.api.auth import CurrentUser, get_user_doc_filter
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Maximum total chunks we feed into the LLM context.
# gpt-4o-mini has a 128K context window (~96K usable for prompt).
# Each chunk is ~500 tokens, so 150 chunks ≈ 75K tokens – within budget.
MAX_CONTEXT_CHUNKS = 150


class Retriever:
    """Orchestrates document retrieval using embeddings and metadata filters."""
    
    def __init__(self, db: Session, current_user: Optional[CurrentUser] = None):
        self.vector_store = VectorStore(db)
        self.embedder = Embedder()
        self.current_user = current_user

        # Derive RBAC policy filter (None → admin / no user → unrestricted)
        if current_user is not None:
            self._doc_filter = get_user_doc_filter(current_user)
            self._tenant_id = current_user.tenant_id
        else:
            self._doc_filter = None
            self._tenant_id = None
        
    def get_relevant_context(self, question: str, entity: str = None, document_type: str = None, document_ids: List[str] = None, limit: int = 10) -> List[Dict]:
        """Retrieves assembly of relevant chunks for a question.
        
        Args:
            question: The natural language question
            entity: Optional company name to filter results
            document_type: Optional document type filter
            document_ids: Optional list of specific doc IDs to search within
            limit: Max number of chunks to return
            
        Returns:
            List of dicts containing 'text' and 'metadata'
        """
        try:
            logger.info(f"Retrieving context for: {question} (entity: {entity}, document_ids: {document_ids})")
            
            # 0. Fast Path: Greetings
            if self._is_greeting(question):
                logger.info("Greeting detected, skipping retrieval")
                return []

            # 1. When specific documents are selected, fetch ALL chunks from
            #    those documents so nothing is missed.  This is the critical
            #    fix for "list all X" type queries.
            if document_ids and len(document_ids) >= 1:
                return self._retrieve_full_documents(document_ids, limit)

            # 2. Infer Intent (Metric vs Explanation)
            intent = self._infer_intent(question)
            logger.info(f"Inferred intent: {intent}")
            
            # 3. Generate embedding for the question
            query_embedding = self.embedder.embed_text(question)
            
            # 4. Standard semantic search (no specific docs selected)
            filters = {}
            if entity:
                filters["entity"] = entity
            if document_type:
                filters["document_type"] = document_type
                
            results = self.vector_store.search(
                query_embedding,
                limit=limit,
                filters=filters,
                tenant_id=self._tenant_id,
                doc_filter=self._doc_filter,
            )
            
            context_chunks = []
            for chunk, distance in results:
                context_chunks.append({
                    "text": chunk.text,
                    "metadata": chunk.metadata_json,
                    "score": 1 - distance
                })
                
            return context_chunks
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise

    def _retrieve_full_documents(
        self,
        document_ids: List[str],
        limit: int,
    ) -> List[Dict]:
        """Retrieve ALL chunks from the selected documents (no semantic filter).

        When a user explicitly selects documents and asks a question like
        'list all orders', every single chunk from those documents is relevant.
        Semantic search would miss chunks whose text doesn't happen to be
        similar to the question.

        If the total number of chunks exceeds MAX_CONTEXT_CHUNKS, we
        keep a proportional share from each document so every doc is
        still represented.
        """
        chunks = self.vector_store.fetch_all_by_doc_ids(
            doc_ids=document_ids,
            tenant_id=self._tenant_id,
            doc_filter=self._doc_filter,
        )

        # Group by doc_id for logging and proportional capping
        by_doc: Dict[str, list] = {}
        for c in chunks:
            by_doc.setdefault(c.doc_id, []).append(c)

        logger.info(
            f"Full-doc retrieval: {len(chunks)} total chunks across "
            f"{len(by_doc)} documents: "
            + ", ".join(f"{did}={len(clist)}" for did, clist in by_doc.items())
        )

        cap = min(limit, MAX_CONTEXT_CHUNKS)

        if len(chunks) <= cap:
            # Everything fits – return all chunks
            return [
                {
                    "text": c.text,
                    "metadata": c.metadata_json,
                    "score": 1.0,  # full-doc fetch, no distance
                    "doc_id": c.doc_id,
                }
                for c in chunks
            ]

        # Too many chunks – take a proportional sample from each doc
        per_doc_quota = max(3, cap // len(by_doc))
        logger.info(f"Capping to {cap} chunks, ~{per_doc_quota} per doc")

        selected: List[Dict] = []
        for doc_id, doc_chunks in by_doc.items():
            # Take first N chunks (they are ordered by chunk index, so they
            # cover the document from top to bottom)
            for c in doc_chunks[:per_doc_quota]:
                selected.append({
                    "text": c.text,
                    "metadata": c.metadata_json,
                    "score": 1.0,
                    "doc_id": c.doc_id,
                })

        logger.info(f"After proportional cap: {len(selected)} chunks selected")
        return selected[:cap]

    def _infer_intent(self, question: str) -> str:
        """Heuristic-based intent inference."""
        q_lower = question.lower()
        
        metric_keywords = ["what was", "amount", "total", "how much", "value", "number", "count", "date", "when", "price", "cost", "quantity"]
        explanation_keywords = ["why", "explain", "describe", "notes", "detail", "policy", "reason", "background", "what does", "what is"]
        analytic_keywords = ["compare", "versus", "vs", "difference", "trend", "change", "growth", "analysis", "summary", "summarize"]
        
        if any(word in q_lower for word in analytic_keywords):
            return "analytical"
        if any(word in q_lower for word in explanation_keywords):
            return "explanation"
        if any(word in q_lower for word in metric_keywords):
            return "metric"
            
        return "general"

    def _is_greeting(self, text: str) -> bool:
        """Checks if a message is a simple greeting or casual query."""
        greetings = [
            "hi", "hello", "hey", "greetings", "good morning", "good afternoon", 
            "good evening", "howdy", "سلام", "مرحبا", "أهلا", "كيف حالك", "how are you",
            "test", "fresa", "who are you", "what can you do"
        ]
        text_clean = text.lower().strip().rstrip('?!.')
        
        if any(text_clean == g for g in greetings):
            return True
        
        if len(text_clean) < 4 and not text_clean.isdigit():
            return True
            
        return False

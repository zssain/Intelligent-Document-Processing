from sqlalchemy.orm import Session
from src.rag.vector_store import VectorStore
from src.rag.embedder import Embedder
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class Retriever:
    """Orchestrates document retrieval using embeddings and metadata filters."""
    
    def __init__(self, db: Session):
        self.vector_store = VectorStore(db)
        self.embedder = Embedder()
        
    def get_relevant_context(self, question: str, entity: str = None, document_type: str = None, document_ids: List[str] = None, limit: int = 10) -> List[Dict]:
        """Retrieves assembly of relevant chunks for a question.
        
        Args:
            question: The natural language question
            entity: Optional company name to filter results
            document_type: Optional document type filter
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

            # 1. Infer Intent (Metric vs Explanation)
            intent = self._infer_intent(question)
            logger.info(f"Inferred intent: {intent}")
            
            # 2. Generate embedding for the question
            query_embedding = self.embedder.embed_text(question)
            
            # 3. Build filters
            filters = {}
            if entity:
                filters["entity"] = entity
            if document_type:
                filters["document_type"] = document_type
            if document_ids:
                filters["document_ids"] = document_ids
                
            # 4. Perform search
            results = self.vector_store.search(query_embedding, limit=limit, filters=filters)
            
            # 5. Format output
            context_chunks = []
            for chunk, distance in results:
                context_chunks.append({
                    "text": chunk.text,
                    "metadata": chunk.metadata_json,
                    "score": 1 - distance # Convert distance to similarity score
                })
                
            return context_chunks
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise

    def _infer_intent(self, question: str) -> str:
        """Heuristic-based intent inference."""
        q_lower = question.lower()
        
        # Keywords suggesting a specific numeric value or data point
        metric_keywords = ["what was", "amount", "total", "how much", "value", "number", "count", "date", "when", "price", "cost", "quantity"]
        # Keywords suggesting a narrative explanation
        explanation_keywords = ["why", "explain", "describe", "notes", "detail", "policy", "reason", "background", "what does", "what is"]
        # Keywords suggesting comparison or analysis
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
        
        # Exact match or starts with a greeting (for short messages)
        if any(text_clean == g for g in greetings):
            return True
        
        # Very short messages (< 4 chars) that aren't numeric
        if len(text_clean) < 4 and not text_clean.isdigit():
            return True
            
        return False

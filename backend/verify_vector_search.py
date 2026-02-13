
import unittest
from unittest.mock import MagicMock, patch
import uuid
import sys
import os

# Add the project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the database models and types before importing VectorStore
mock_models = MagicMock()
mock_pgvector = MagicMock()

with patch.dict('sys.modules', {
    'pydantic_settings': MagicMock(),
    'pydantic': MagicMock(),
    'src.database.models': mock_models,
    'pgvector.sqlalchemy': mock_pgvector,
    'config.settings': MagicMock()
}):
    from src.rag.vector_store import VectorStore

class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.vs = VectorStore(self.db)
        
    def test_search_with_document_ids(self):
        # Setup
        query_embedding = [0.1] * 1536
        doc_ids = [str(uuid.uuid4())]
        filters = {"document_ids": doc_ids}
        
        # Mock query chain
        mock_query = self.db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = ["result"]
        
        # Execute
        results = self.vs.search(query_embedding, filters=filters)
        
        # Verify
        self.assertEqual(results, ["result"])
        # Check if filter was called with the document_id
        # We can't easily check the exact SQL expression without more complex mocking, 
        # but we can see if filter was called.
        self.assertTrue(mock_query.filter.called)
        
    def test_search_without_document_ids(self):
        # Setup
        query_embedding = [0.1] * 1536
        
        # Mock query chain
        mock_query = self.db.query.return_value
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = ["result"]
        
        # Execute
        results = self.vs.search(query_embedding)
        
        # Verify
        self.assertEqual(results, ["result"])
        # Should not call filter if no filters provided
        self.assertFalse(mock_query.filter.called)

if __name__ == '__main__':
    unittest.main()


import sys
import os
import json
import uuid

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.base import SessionLocal
from src.rag.retriever import Retriever
from src.database.models import Document

def test_retrieval(question, document_ids=None):
    db = SessionLocal()
    try:
        retriever = Retriever(db)
        
        print(f"\n--- Testing Retrieval ---")
        print(f"Question: {question}")
        if document_ids:
            print(f"Filtering by Document IDs: {document_ids}")
            # Verify IDs exist in DB
            for d_id in document_ids:
                doc = db.query(Document).filter(Document.id == uuid.UUID(d_id)).first()
                if doc:
                    print(f"  [OK] Found document: {doc.filename} ({d_id})")
                else:
                    print(f"  [ERROR] Document ID NOT FOUND: {d_id}")
        else:
            print("Searching across ALL documents")

        chunks = retriever.get_relevant_context(
            question,
            document_ids=document_ids,
            limit=5
        )

        print(f"\nFound {len(chunks)} relevant chunks:")
        for i, chunk in enumerate(chunks):
            print(f"\n[{i+1}] Source: {chunk['metadata'].get('statement', 'Unknown')}")
            print(f"    Similarity Score: {chunk['score']:.4f}")
            print(f"    Text Preview: {chunk['text'][:200]}...")
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Retrieval test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_retrieval.py \"Your question here\" [doc_id1,doc_id2,...]")
        sys.exit(1)

    query = sys.argv[1]
    doc_ids = None
    if len(sys.argv) > 2:
        doc_ids = sys.argv[2].split(',')

    test_retrieval(query, doc_ids)

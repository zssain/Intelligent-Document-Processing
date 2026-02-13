import sys
import os

# uv run python tests/verify_v3.py

from src.database.base import SessionLocal
from src.rag.retriever import Retriever

def test_lenient_entity_search():
    db = SessionLocal()
    retriever = Retriever(db)
    
    question = "What is the revenue for cubicle cold solutions?"
    entity = "cubicle cold solutions"
    
    print(f"Testing retrieval for entity: '{entity}'")
    context = retriever.get_relevant_context(question, entity=entity)
    
    print(f"Number of chunks found: {len(context)}")
    if len(context) > 0:
        print("✅ SUCCESS: Found chunks despite name mismatch.")
        for i, c in enumerate(context[:2]):
            print(f"Chunk {i+1} score: {c['score']:.4f}")
            print(f"Chunk {i+1} entity: {c['metadata'].get('entity')}")
    else:
        print("❌ FAILURE: No chunks found.")

if __name__ == "__main__":
    try:
        test_lenient_entity_search()
    except Exception as e:
        print(f"Test failed: {e}")

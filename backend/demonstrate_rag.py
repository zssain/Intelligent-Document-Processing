import requests
import json
import time
import os

BASE_URL = "http://localhost:8000/api/v1/rag"

def test_pipeline():
    print("=== Financial RAG Pipeline Demonstration ===\n")
    
    # 1. Ingest
    print("[1] Ingesting document...")
    file_path = "audit_report_0001.pdf"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please ensure a test PDF exists.")
        return

    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/ingest", files=files)
    
    if response.status_code != 200:
        print(f"Ingestion failed: {response.text}")
        return
    
    ingest_data = response.json()
    doc_id = ingest_data["document_id"]
    print(f"Success! Document ID: {doc_id}")
    print(f"Chunks created: {ingest_data['chunks_count']}\n")

    # Wait a bit for indexing (though it's sync in this impl)
    time.sleep(1)

    # 2. Query - Metric
    print("[2] Querying for a specific metric...")
    query_payload = {
        "question": "What was the total revenue?",
        "entity": "CUBICLE COLD STORAGE PRIVATE LIMITED"
    }
    response = requests.post(f"{BASE_URL}/query", json=query_payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Q: {query_payload['question']}")
        print(f"A: {result['answer']}")
        print(f"Sources: {result['sources']}\n")
    else:
        print(f"Query failed: {response.text}")

    # 3. Query - Explanation (Semantic)
    print("[3] Querying for a narrative explanation...")
    query_payload = {
        "question": "Explain the major observations from the report.",
        "entity": "CUBICLE COLD STORAGE PRIVATE LIMITED"
    }
    response = requests.post(f"{BASE_URL}/query", json=query_payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Q: {query_payload['question']}")
        print(f"A: {result['answer']}")
        print(f"Sources: {result['sources']}\n")

    # 4. Check for Hallucination Prevention
    print("[4] Testing hallucination prevention...")
    query_payload = {
        "question": "What was the revenue in the year 1990?",
        "entity": "CUBICLE COLD STORAGE PRIVATE LIMITED"
    }
    response = requests.post(f"{BASE_URL}/query", json=query_payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Q: {query_payload['question']}")
        print(f"A: {result['answer']}\n")

if __name__ == "__main__":
    test_pipeline()

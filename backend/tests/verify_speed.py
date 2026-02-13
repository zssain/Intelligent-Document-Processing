import time
import json
import requests
import sys

# Usage: python tests/verify_speed.py

BASE_URL = "http://127.0.0.1:8000/api/v1/rag"

def test_stream(question, label):
    print(f"\n--- Testing {label}: '{question}' ---")
    
    start_time = time.time()
    first_token_time = None
    full_response = ""
    
    try:
        response = requests.post(
            f"{BASE_URL}/query/stream",
            json={"question": question, "language": "english"},
            stream=True
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return

        for line in response.iter_lines():
            if line:
                if first_token_time is None:
                    first_token_time = time.time()
                
                chunk = json.loads(line.decode('utf-8'))
                if "content" in chunk:
                    full_response += chunk["content"]
                elif "sources" in chunk:
                    print(f"Sources: {chunk['sources']}")
                elif "error" in chunk:
                    print(f"❌ API Error: {chunk['error']}")
        
        end_time = time.time()
        
        print(f"Time to first token: {first_token_time - start_time:.4f}s")
        print(f"Total time: {end_time - start_time:.4f}s")
        print(f"Response preview: {full_response[:100]}...")
        
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    # 1. Test Greeting (Fast Path)
    test_stream("Hi there", "Greeting (Fast Path)")
    
    # 2. Test Document Query (Standard Path)
    test_stream("What is the revenue for Cubicle Cold Solutions?", "Document Query")

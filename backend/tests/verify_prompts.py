import sys
import os
import json

# This script should be run from the backend directory using:
# uv run python tests/verify_prompts.py

from src.rag.qa import QualityAssurance

def test_prompt_logic():
    qa = QualityAssurance()
    
    # Test 1: Out of scope question
    print("Testing Out of Scope Question...")
    out_of_scope_q = "What is the weather in Paris today?"
    # Provide some irrelevant context
    context = [{"text": "The company revenue was $1M.", "metadata": {"statement": "Financial Report"}, "score": 0.3}]
    result = qa.answer_question(out_of_scope_q, context)
    print(f"Q: {out_of_scope_q}")
    print(f"A: {result['answer']}")
    
    expected_rejection = "Financial bot can only help with the uploaded documents it has respectfully"
    if expected_rejection in result['answer']:
        print("✅ SUCCESS: Correctly rejected out-of-scope question.")
    else:
        print("❌ FAILURE: Did not use specific rejection message.")

    print("-" * 20)

    # Test 2: Lenience (Paraphrased question)
    print("Testing Lenience (Paraphrased question)...")
    lenient_q = "How much money did the firm bring in?"
    # Context contains "revenue" but not "money brought in"
    context = [{"text": "Total revenue for the period was $5,000,000.", "metadata": {"statement": "Income Statement"}, "score": 0.9}]
    result = qa.answer_question(lenient_q, context)
    print(f"Q: {lenient_q}")
    print(f"A: {result['answer']}")
    
    if "$5,000,000" in result['answer']:
        print("✅ SUCCESS: Correctly answered paraphrased question.")
    else:
        print("❌ FAILURE: Failed to answer paraphrased question.")

    print("-" * 20)

    # Test 3: Empty Context
    print("Testing Empty Context...")
    result = qa.answer_question("Where is the CEO?", [])
    print(f"A: {result['answer']}")
    if expected_rejection in result['answer']:
        print("✅ SUCCESS: Correctly handled empty context.")
    else:
        print("❌ FAILURE: Failed to handle empty context with respectful message.")

if __name__ == "__main__":
    try:
        test_prompt_logic()
    except Exception as e:
        print(f"Test failed with error: {e}")

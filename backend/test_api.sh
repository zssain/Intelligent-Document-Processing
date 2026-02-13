#!/bin/bash
# Test health endpoint
echo "=== Health Check ==="
curl -s http://localhost:8000/api/v1/health
echo ""
echo ""

# Test streaming query
echo "=== Stream Query Test ==="
curl -s -X POST http://localhost:8000/api/v1/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "summarise the documents", "language": "english"}' \
  --max-time 30
echo ""
echo "=== Done ==="

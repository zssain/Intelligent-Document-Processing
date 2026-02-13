#!/bin/bash
# Start server in background, wait for it, then test
cd /Users/zuhairhussain/Desktop/bluetide-B-5-2/backend

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 1

# Start server in background
/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to be ready
echo "Waiting for server..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    sleep 1
done

# Test health
echo ""
echo "=== Health Check ==="
curl -s http://localhost:8000/api/v1/health
echo ""

# Test streaming query 
echo ""
echo "=== Stream Query Test ==="
curl -s -X POST http://localhost:8000/api/v1/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "summarise the documents", "language": "english"}' \
  --max-time 60
echo ""
echo "=== Tests Complete ==="

# Keep server running
echo "Server still running as PID $SERVER_PID"
wait $SERVER_PID

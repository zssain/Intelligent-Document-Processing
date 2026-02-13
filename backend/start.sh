#!/bin/bash
cd /Users/zuhairhussain/Desktop/bluetide-B-5-2/backend
exec /Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

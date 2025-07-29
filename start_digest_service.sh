#!/bin/bash
# Start Digest service from root directory
cd "$(dirname "$0")"
uv run uvicorn services.digest-service.app.main:app --host 0.0.0.0 --port 8002 --reload
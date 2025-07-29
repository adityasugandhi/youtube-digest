#!/bin/bash
# Start YouTube service from root directory
cd "$(dirname "$0")"
uv run uvicorn services.youtube-service.app.main:app --host 0.0.0.0 --port 8001 --reload
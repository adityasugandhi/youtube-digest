#!/bin/bash

# YouTube Digest Backend - Start Services for Testing

echo "🚀 Starting YouTube Digest Backend Services"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "   Please ensure .env file exists with YouTube API key"
    exit 1
fi

# Check if uv environment is set up
if [ ! -d .venv ]; then
    echo "📦 Setting up uv environment..."
    uv sync
fi

echo "🔍 Checking services..."

# Function to check if port is available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Port $1 is already in use"
        return 1
    fi
    return 0
}

# Check ports
if ! check_port 8001; then
    echo "   YouTube service port (8001) is busy"
fi

if ! check_port 8002; then
    echo "   Digest service port (8002) is busy"
fi

echo ""
echo "🎯 To start the services manually:"
echo ""
echo "Terminal 1 (YouTube Service):"
echo "cd youtube-digest-backend"
echo "uv run uvicorn services.youtube-service.app.main:app --host 0.0.0.0 --port 8001 --reload"
echo ""
echo "Terminal 2 (Digest Service):"  
echo "cd youtube-digest-backend"
echo "uv run uvicorn services.digest-service.app.main:app --host 0.0.0.0 --port 8002 --reload"
echo ""
echo "Terminal 3 (Test):"
echo "cd youtube-digest-backend"
echo "uv run python test_updated_backend.py"
echo ""
echo "📊 Service URLs:"
echo "   YouTube Service: http://localhost:8001"
echo "   Digest Service: http://localhost:8002"
echo "   YouTube API Docs: http://localhost:8001/docs"
echo "   Digest API Docs: http://localhost:8002/docs"
echo ""
echo "🧪 Test Endpoints:"
echo "   Resolve Handle: curl http://localhost:8001/api/v1/streams/resolve/@amitinvesting"
echo "   Get Streams: curl 'http://localhost:8001/api/v1/streams/channel/@amitinvesting/completed?max_results=5'"
echo "   Health Check: curl http://localhost:8001/health"
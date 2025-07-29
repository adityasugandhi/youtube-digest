#!/bin/bash

# YouTube Digest Backend - Development Startup Script

set -e

echo "🚀 Starting YouTube Digest Backend Development Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please update .env file with your API keys before proceeding"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found. Installing uv..."
    pip install uv
fi

# Create uv environment and install dependencies
echo "📦 Setting up uv environment and installing dependencies..."
uv venv
source .venv/bin/activate
uv pip install -e .

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."
docker-compose ps

echo "✅ Development environment ready!"
echo ""
echo "🔗 Service URLs:"
echo "   - YouTube Service: http://localhost:8001"
echo "   - Digest Service: http://localhost:8002"
echo "   - API Gateway: http://localhost:80"
echo "   - YouTube API Docs: http://localhost:8001/docs"
echo "   - Digest API Docs: http://localhost:8002/docs"
echo ""
echo "🎯 To start the services:"
echo "   uv run uvicorn services.youtube-service.app.main:app --host 0.0.0.0 --port 8001 --reload"
echo "   uv run uvicorn services.digest-service.app.main:app --host 0.0.0.0 --port 8002 --reload"
echo ""
echo "🛑 To stop services: docker-compose down"
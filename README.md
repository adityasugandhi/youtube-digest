# YouTube Live Stream Digest Backend

A microservices architecture for processing YouTube live streams and generating Robinhood Cortex-style financial digests using AI.

## ✅ Current Status: Configuration Fixed, Ready for Testing

**Latest Checkpoint**: All configuration and import issues resolved. Services can run independently from their own directories with Groq DeepSeek-R1-Distill-Llama-70B integration.

## 🏗️ Architecture

- **YouTube Service**: Extracts transcripts from completed YouTube live streams
- **Digest Generator**: Creates AI-powered financial digests in Robinhood's bullet-point format
- **Stream Processor**: Handles batch processing and workflow orchestration
- **API Gateway**: NGINX-based request routing and load balancing

## 🚀 Quick Start

### Prerequisites

- **uv** Python package manager
- **Docker & Docker Compose**
- **API Keys**: YouTube Data API, OpenAI, Anthropic (optional)

### Development Setup

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd youtube-digest-backend

# Copy environment template
cp .env.example .env

# Add your API keys to .env file
# YOUTUBE_API_KEY=your_youtube_api_key
# OPENAI_API_KEY=your_openai_api_key
```

2. **Start development environment:**
```bash
# Run the setup script
./scripts/start.sh

# Or manually:
uv venv
source .venv/bin/activate
uv pip install -e .
```

3. **Start services:**
```bash
# YouTube Service (Terminal 1)
cd services/youtube-service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Digest Service (Terminal 2)
cd services/digest-service  
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

4. **Start automation service:**
```bash
# Automation Service (Terminal 3)
cd services/automation
uv run uvicorn api:app --host 0.0.0.0 --port 8003 --reload
```

5. **Access services:**
- **API Gateway**: http://localhost:80
- **YouTube Service**: http://localhost:8001
- **Digest Service**: http://localhost:8002
- **Automation Service**: http://localhost:8003
- **API Documentation**: 
  - YouTube: http://localhost:8001/docs
  - Digest: http://localhost:8002/docs
  - Automation: http://localhost:8003/docs

## 📚 API Reference

### 🎬 YouTube Service (Port 8001)

#### Transcripts
```bash
# Single transcript
curl "http://localhost:8001/api/v1/transcripts/VIDEO_ID"

# Batch transcripts
curl -X POST "http://localhost:8001/api/v1/transcripts/batch" \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["video1", "video2"], "concurrent_limit": 5}'
```

#### Streams & Channels
```bash
# Get completed streams from channel
curl "http://localhost:8001/api/v1/streams/channel/CHANNEL_ID/completed?max_results=10&include_transcripts=true"

# Resolve channel handle to ID
curl "http://localhost:8001/api/v1/streams/resolve/@channelhandle"

# Get video info
curl "http://localhost:8001/api/v1/streams/VIDEO_ID/info"
```

### 🤖 Digest Service (Port 8002)

#### Generate Digests
```bash
# Single digest generation
curl -X POST "http://localhost:8002/api/v1/digests/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123",
    "transcript": "transcript text...",
    "metadata": {
      "channel_name": "CNBC",
      "video_title": "Fed Meeting Live"
    },
    "focus_areas": "Federal Reserve policy"
  }'

# Batch digest generation
curl -X POST "http://localhost:8002/api/v1/digests/batch" \
  -H "Content-Type: application/json" \
  -d '[{"video_id": "video1", "transcript": "text1"}, {"video_id": "video2", "transcript": "text2"}]'

# Get digest by ID
curl "http://localhost:8002/api/v1/digests/DIGEST_ID"
```

#### Pipeline Processing
```bash
# Process single video stream
curl -X POST "http://localhost:8002/api/v1/pipeline/process-stream/VIDEO_ID"

# Process entire channel
curl -X POST "http://localhost:8002/api/v1/pipeline/process-channel/CHANNEL_ID"
```

### 🔄 Automation Service (Port 8003)

#### Semantic Search
```bash
# Advanced semantic search
curl -X POST "http://localhost:8003/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tesla earnings and stock predictions",
    "n_results": 10,
    "channel_filter": "Amit Investing",
    "category_filter": "investing"
  }'

# Recent videos
curl "http://localhost:8003/api/v1/search/recent?n_results=20&channel_filter=Meet%20Kevin"

# Channel-specific search
curl "http://localhost:8003/api/v1/search/by-channel/Amit%20Investing?query=NVIDIA&n_results=5"

# Search video chunks
curl -X POST "http://localhost:8003/api/v1/search/chunks" \
  -H "Content-Type: application/json" \
  -d '{"query": "Fed rate decision", "n_results": 5}'

# Get video chunks
curl "http://localhost:8003/api/v1/video/VIDEO_ID/chunks"
```

#### Channel Management
```bash
# List all channels
curl "http://localhost:8003/api/v1/channels"

# Get channel videos
curl "http://localhost:8003/api/v1/channel/CHANNEL_ID/videos"
```

#### Analytics & Insights
```bash
# Get video insights
curl "http://localhost:8003/api/v1/insights/VIDEO_ID"

# System statistics
curl "http://localhost:8003/api/v1/stats"

# Supadata statistics
curl "http://localhost:8003/api/v1/stats/supadata"
```

#### Health Monitoring
```bash
# Quick health check
curl "http://localhost:8003/health"

# Full health check
curl "http://localhost:8003/health/full"

# Health summary
curl "http://localhost:8003/health/summary"
```

## 🐳 Docker Deployment

### Development
```bash
docker-compose up -d
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Example Response

### Digest Response
```json
{
  "video_id": "abc123",
  "title": "📊 Fed Meeting - Hawkish Stance on Inflation",
  "bullet_points": [
    {
      "text": "Fed raises rates 0.75% citing persistent inflation above 6%",
      "word_count": 10,
      "has_numbers": true
    },
    {
      "text": "Powell signals more aggressive tightening if inflation doesn't cool",
      "word_count": 10,
      "has_numbers": false
    }
  ],
  "quality_score": 85.5,
  "ai_model": "gpt-4o",
  "tokens_used": 1250,
  "processing_time": 2.3,
  "confidence_score": 0.92,
  "generated_at": "2025-07-28T20:00:00Z"
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API key | Required |
| `GEMINI_API_KEY` | Gemini API key for AI summaries | Required |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback) | Optional |
| `DATABASE_URL` | PostgreSQL connection string | Optional |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `CHROMA_DB_PATH` | ChromaDB storage path | `/app/data/chroma_db` |
| `AUTOMATION_API_PORT` | Automation service port | `8003` |
| `RUN_ON_STARTUP` | Run pipeline on service startup | `false` |
| `RATE_LIMIT_REQUESTS` | Requests per hour | `100` |

## 🧪 Testing

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=services

# Run linting
black services/
isort services/
flake8 services/
```

## 📝 Development Guidelines

- Always use **uv** for Python package management
- Always use **TailwindCSS** for styling (when applicable)
- Run `npm lint` after making changes (if Node.js components exist)
- Follow FastAPI best practices
- Use type hints throughout the codebase

## 🔍 Monitoring

- **Health Checks**: `/health` endpoint on each service
- **Metrics**: Prometheus metrics exposed
- **Logging**: Structured logging with configurable levels
- **Tracing**: Request timing and performance metrics

## 🤖 Automation Features

### ✅ Automated Pipeline
- **Hourly Processing**: Automatically fetches and processes videos from configured channels
- **AI Summarization**: Generates Robinhood Cortex-style financial summaries using Gemini
- **Vector Database**: Stores summaries with embeddings in ChromaDB for semantic search
- **Smart Duplicate Detection**: Prevents reprocessing of existing videos
- **Rate Limiting**: Respects API quotas with intelligent delays

### ✅ Semantic Search
- **Vector Embeddings**: Advanced semantic search across all video summaries
- **Multi-filter Support**: Filter by channel, presenter, category, date
- **Similarity Scoring**: Relevance ranking for search results
- **Chunk-based Search**: Search within video transcript segments

### ✅ Channel Management
- **Dynamic Configuration**: Add/remove channels via API
- **Enable/Disable**: Control which channels are processed
- **Metadata Tracking**: Channel info, presenters, categories
- **Statistics**: Processing stats and performance metrics

## 🚧 TODO

- [ ] Implement database models and migrations
- [ ] Add comprehensive test suite
- [ ] Set up CI/CD pipeline
- [ ] Add Kubernetes deployment manifests
- [x] Implement automation service with scheduling
- [x] Add vector database with semantic search
- [ ] Add authentication and authorization
- [ ] Set up monitoring dashboards

## 📖 Documentation

- [API Documentation](docs/api/)
- [Architecture Guide](docs/architecture/)
- [Deployment Guide](docs/deployment/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
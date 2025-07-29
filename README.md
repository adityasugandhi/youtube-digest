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

4. **Access services:**
- **API Gateway**: http://localhost:80
- **YouTube Service**: http://localhost:8001
- **Digest Service**: http://localhost:8002
- **API Documentation**: 
  - YouTube: http://localhost:8001/docs
  - Digest: http://localhost:8002/docs

## 📚 API Usage

### Extract Transcript

```bash
# Single transcript
curl "http://localhost:8001/api/v1/transcripts/VIDEO_ID"

# Batch transcripts
curl -X POST "http://localhost:8001/api/v1/transcripts/batch" \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["video1", "video2"], "concurrent_limit": 5}'
```

### Generate Digest

```bash
# Generate digest
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
```

### Get Channel Streams

```bash
# Get completed streams from channel
curl "http://localhost:8001/api/v1/streams/channel/CHANNEL_ID/completed?max_results=10&include_transcripts=true"
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
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
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

## 🚧 TODO

- [ ] Implement database models and migrations
- [ ] Add comprehensive test suite
- [ ] Set up CI/CD pipeline
- [ ] Add Kubernetes deployment manifests
- [ ] Implement stream processor with Celery
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
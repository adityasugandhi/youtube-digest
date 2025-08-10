# YouTube Automation Pipeline - Production

A production-ready service for automated YouTube video transcription, summarization, and semantic search.

## Features

- **Multi-tier transcript extraction**: YouTube API → Supabase API fallback
- **Intelligent caching**: Video transcripts cached by ID to minimize API calls
- **Semantic search**: ChromaDB vector database for similarity search
- **Structured summaries**: Timestamps, stock tickers, and investment insights
- **Channel tracking**: Monitors 5 most recent videos per channel
- **Production ready**: Docker, health checks, logging, non-root user

## Quick Start

### Docker (Recommended)

```bash
# Build the image
docker build -t youtube-automation .

# Run with environment variables
docker run -d \
  --name youtube-automation \
  -p 8003:8003 \
  -e YOUTUBE_API_KEY="your_key_here" \
  -e SUPABASE_YOUTUBE_API="your_key_here" \
  -e GEMINI_API_KEY="your_key_here" \
  -v /var/lib/youtube-automation:/var/lib/youtube-automation \
  -v /var/log/youtube-automation:/var/log/youtube-automation \
  youtube-automation
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (see production.env)
export YOUTUBE_API_KEY="your_key_here"
export SUPABASE_YOUTUBE_API="your_key_here" 
export GEMINI_API_KEY="your_key_here"

# Run the service
python start_automation.py --mode combined
```

## API Endpoints

### Search
- `POST /search` - Semantic video search
- `GET /search/recent` - Recent videos
- `GET /search/by-channel/{name}` - Search within channel

### Information
- `GET /health` - Service health check
- `GET /stats` - Database statistics
- `GET /channels` - List enabled channels

## Configuration

Environment variables (see `production.env`):

- `YOUTUBE_API_KEY` - YouTube Data API v3 key
- `SUPABASE_YOUTUBE_API` - Supabase transcript API key  
- `GEMINI_API_KEY` - Google Gemini API key
- `CHROMA_DB_PATH` - Vector database storage path
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)

## Service Modes

- `--mode combined` - API server + scheduler (default)
- `--mode api` - API server only
- `--mode scheduler` - Background processing only

## Monitoring

- Health check: `GET /health`
- Docker health check enabled
- Structured logging to files and stdout
- Database statistics available

## Security

- Runs as non-root user in Docker
- CORS configured for production domains
- No test/debug endpoints in production
- Environment variable validation

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌───────────────┐
│   YouTube API   │───▶│   Pipeline   │───▶│   ChromaDB    │
└─────────────────┘    └──────────────┘    └───────────────┘
                               │
                       ┌──────────────┐
                       │ Supabase API │
                       └──────────────┘
                               │
                       ┌──────────────┐    ┌───────────────┐
                       │  FastAPI     │───▶│  Search API   │
                       └──────────────┘    └───────────────┘
```

## Channel Configuration

Edit `youtube_creators_list.json` to add/remove channels:

```json
{
  "channels": [
    {
      "channel_name": "Channel Name",
      "channel_url": "https://youtube.com/@channelhandle",
      "presenters": ["Host Name"],
      "category": "investing",
      "enabled": true
    }
  ]
}
```

## Performance

- Transcript caching reduces API calls by 90%+
- Processes 5 videos per channel every hour
- Supports multiple channels concurrently
- Vector search sub-second response times

## Troubleshooting

Check logs:
```bash
# Docker
docker logs youtube-automation

# Manual
tail -f /var/log/youtube-automation/automation.log
```

Health check:
```bash
curl http://localhost:8003/health
```

Database stats:
```bash
curl http://localhost:8003/stats
```
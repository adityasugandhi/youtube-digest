# YouTube Automation Pipeline Guide

## 🚀 Overview

The YouTube Automation Pipeline is a complete system that automatically:
- Fetches latest videos from your configured YouTube channels every hour
- Extracts transcripts and generates AI-powered financial summaries
- Stores summaries with embeddings in a vector database (ChromaDB)
- Provides powerful search APIs for your frontend

## 📋 Features

### ✅ Automated Processing
- **Hourly scheduling** of all enabled channels
- **Transcript extraction** using YouTube API
- **AI summarization** with Gemini (Robinhood Cortex style)
- **Vector embeddings** for semantic search
- **Duplicate detection** prevents reprocessing

### ✅ Vector Database (ChromaDB)
- **Semantic search** across all video summaries
- **Metadata filtering** by channel, presenter, category
- **Similarity scoring** for relevant results
- **Persistent storage** with automatic embedding generation

### ✅ RESTful API
- **Search endpoints** for semantic queries
- **Channel management** (add/remove/enable/disable)
- **Pipeline controls** (manual runs, testing)
- **Database statistics** and export functions

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   YouTube API   │───▶│  Summarization   │───▶│   Vector DB     │
│                 │    │    Pipeline      │    │   (ChromaDB)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                       ┌────────▼────────┐              │
                       │   Scheduler     │              │
                       │  (Every Hour)   │              │
                       └─────────────────┘              │
                                                        │
┌─────────────────┐    ┌──────────────────┐           │
│   Frontend      │◀───│   REST API       │◀──────────┘
│   Integration   │    │   (Port 8003)    │
└─────────────────┘    └──────────────────┘
```

## 🔧 Setup & Configuration

### 1. Environment Variables

Add to your `.env` file:
```bash
# Required API Keys
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
CHROMA_DB_PATH=/app/data/chroma_db
AUTOMATION_API_PORT=8003
RUN_ON_STARTUP=false
```

### 2. YouTube Creators Configuration

Edit `youtube_creators_list.json`:
```json
[
  {
    "channel_name": "Amit Investing",
    "channel_url": "https://www.youtube.com/@amitinvesting",
    "presenters": ["Amit Kukreja"],
    "channel_id": "UCjZnbgPb08NFg7MHyPQRZ3Q",
    "enabled": true,
    "category": "investing"
  }
]
```

### 3. Docker Deployment

```bash
# Start all services including automation
docker-compose up -d

# Check logs
docker-compose logs -f automation-service

# Check health
curl http://localhost/health/automation
```

## 📡 API Endpoints

### Search Endpoints

#### Semantic Search
```bash
POST /api/v1/search
{
  "query": "Tesla earnings and stock predictions",
  "n_results": 10,
  "channel_filter": "Amit Investing",
  "category_filter": "investing"
}
```

#### Recent Videos
```bash
GET /api/v1/search/recent?n_results=20&channel_filter=Meet%20Kevin
```

#### Channel-Specific Search
```bash
GET /api/v1/search/by-channel/Amit%20Investing?query=NVIDIA&n_results=5
```

#### Presenter Search
```bash
GET /api/v1/search/by-presenter/Kevin?n_results=10
```

### Channel Management

#### List Channels
```bash
GET /api/v1/channels
```

#### Add Channel
```bash
POST /api/v1/channels
{
  "channel_name": "New Channel",
  "channel_url": "https://www.youtube.com/@newchannel",
  "presenters": ["Presenter Name"],
  "category": "investing",
  "enabled": true
}
```

#### Enable/Disable Channel
```bash
PUT /api/v1/channels/Amit%20Investing/enable?enabled=true
```

### Pipeline Control

#### Run Pipeline Once
```bash
POST /pipeline/run
```

#### Test Pipeline
```bash
POST /pipeline/test?channel_name=Amit%20Investing
```

#### Get Statistics
```bash
GET /pipeline/stats
```

### Database Management

#### Database Stats
```bash
GET /api/v1/database/stats
```

#### Export All Data
```bash
GET /export/all
```

## 🔍 Frontend Integration

### Update youtubeDigest.ts

```typescript
class YouTubeDigestAPI {
  private automationServiceUrl = 'http://localhost'  // NGINX gateway
  
  // New semantic search method
  async searchVideos(query: string, options: {
    nResults?: number;
    channelFilter?: string;
    categoryFilter?: string;
  } = {}): Promise<SearchResult[]> {
    const response = await fetch(`${this.automationServiceUrl}/api/v1/search`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        query,
        n_results: options.nResults || 10,
        channel_filter: options.channelFilter,
        category_filter: options.categoryFilter
      })
    })
    
    return await response.json()
  }
  
  // Get recent videos
  async getRecentVideos(nResults: number = 20): Promise<VideoResult[]> {
    const response = await fetch(
      `${this.automationServiceUrl}/api/v1/search/recent?n_results=${nResults}`,
      { headers: this.getAuthHeaders() }
    )
    
    return await response.json()
  }
  
  // Channel-specific search
  async searchChannelVideos(channelName: string, query?: string): Promise<VideoResult[]> {
    const url = new URL(`${this.automationServiceUrl}/api/v1/search/by-channel/${encodeURIComponent(channelName)}`)
    if (query) url.searchParams.set('query', query)
    
    const response = await fetch(url.toString(), { headers: this.getAuthHeaders() })
    return await response.json()
  }
  
  // Get available channels
  async getChannels(): Promise<Channel[]> {
    const response = await fetch(`${this.automationServiceUrl}/api/v1/channels`, {
      headers: this.getAuthHeaders()
    })
    
    return await response.json()
  }
}
```

### React Component Example

```typescript
import { useState, useEffect } from 'react'

export function VideoSearchComponent() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [channels, setChannels] = useState([])
  const [selectedChannel, setSelectedChannel] = useState('')
  
  useEffect(() => {
    // Load available channels
    youtubeDigestAPI.getChannels().then(setChannels)
  }, [])
  
  const handleSearch = async () => {
    const searchResults = await youtubeDigestAPI.searchVideos(query, {
      channelFilter: selectedChannel || undefined,
      nResults: 15
    })
    setResults(searchResults)
  }
  
  return (
    <div className="video-search">
      <div className="search-controls">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search financial insights..."
          className="search-input"
        />
        
        <select 
          value={selectedChannel} 
          onChange={(e) => setSelectedChannel(e.target.value)}
          className="channel-filter"
        >
          <option value="">All Channels</option>
          {channels.map(channel => (
            <option key={channel.channel_name} value={channel.channel_name}>
              {channel.channel_name}
            </option>
          ))}
        </select>
        
        <button onClick={handleSearch} className="search-button">
          Search
        </button>
      </div>
      
      <div className="results">
        {results.map(result => (
          <div key={result.video_id} className="result-card">
            <h3>{result.metadata.title}</h3>
            <p><strong>{result.metadata.channel_name}</strong> • {result.metadata.presenters.join(', ')}</p>
            <div className="summary">{result.summary}</div>
            <div className="similarity">Relevance: {(result.similarity_score * 100).toFixed(1)}%</div>
            <a href={result.metadata.video_url} target="_blank" rel="noopener noreferrer">
              Watch Video →
            </a>
          </div>
        ))}
      </div>
    </div>
  )
}
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Service health
curl http://localhost/health/automation

# Database stats
curl http://localhost/api/v1/database/stats

# Pipeline statistics
curl http://localhost/pipeline/stats
```

### Logs
```bash
# Container logs
docker-compose logs -f automation-service

# Application logs
docker exec -it youtube-digest-backend_automation-service_1 tail -f automation.log
```

### Manual Operations
```bash
# Test single channel
curl -X POST "http://localhost/pipeline/test?channel_name=Amit%20Investing"

# Run pipeline immediately
curl -X POST "http://localhost/pipeline/run"

# Export all data
curl "http://localhost/export/all" > backup.json
```

## 🔧 Troubleshooting

### Common Issues

1. **No transcripts found**
   - Check if videos have closed captions enabled
   - Some live streams may not have transcripts immediately

2. **Gemini API errors**
   - Verify GEMINI_API_KEY is correct
   - Check API quotas and rate limits

3. **YouTube API errors**
   - Verify YOUTUBE_API_KEY is correct
   - Check API quotas (10,000 requests/day default)

4. **ChromaDB errors**
   - Ensure sufficient disk space for vector storage
   - Check file permissions on CHROMA_DB_PATH

### Performance Optimization

- **Batch processing**: Pipeline processes 5 videos per channel per hour
- **Rate limiting**: 2-5 second delays between API calls
- **Caching**: Vector embeddings stored permanently
- **Memory**: ChromaDB uses efficient disk-based storage

## 🚀 Production Considerations

1. **API Quotas**: Monitor YouTube and Gemini API usage
2. **Storage**: Vector database grows ~1MB per 100 videos
3. **Performance**: Full pipeline run takes 5-15 minutes for 9 channels
4. **Reliability**: Built-in error handling and retry logic
5. **Scaling**: Can easily add more channels or adjust frequency

The system is designed to run continuously and build a comprehensive knowledge base of financial YouTube content that your frontend can query instantly without additional API costs.
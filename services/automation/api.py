"""
Production FastAPI endpoints for the YouTube automation pipeline
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from groq import Groq

from models import CreatorListManager
from qdrant_vector_db import QdrantVectorDB
from health_monitor import HealthMonitor
from supadata_rate_limiter import get_rate_limiter

# Initialize FastAPI app
app = FastAPI(
    title="YouTube Automation Pipeline API",
    description="Production YouTube summarization and search API",
    version="1.0.0",
)

# Production CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Configure for your domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize services
creators_file = os.path.join(os.path.dirname(__file__), "youtube_creators_list.json")
creator_manager = CreatorListManager(creators_file)
vector_db = QdrantVectorDB()
health_monitor = HealthMonitor()

logger = logging.getLogger(__name__)


# Pydantic models
class SearchRequest(BaseModel):
    query: str
    n_results: int = 10
    channel_filter: Optional[str] = None
    category_filter: Optional[str] = None


class SearchResult(BaseModel):
    video_id: str
    summary: str
    metadata: Dict[str, Any]
    similarity_score: float


class InsightResult(BaseModel):
    video_id: str
    video_title: str
    channel_name: str
    insights: Dict[str, Any]
    generated_at: str


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_stats = vector_db.get_stats()
        return {
            "status": "healthy",
            "service": "youtube-automation-pipeline",
            "database_documents": db_stats.get("total_documents", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service unavailable")


# Search endpoints
@app.post("/search", response_model=List[SearchResult])
async def search_videos(request: SearchRequest):
    """Search for videos using semantic similarity"""
    try:
        results = vector_db.search_similar(
            query=request.query,
            n_results=request.n_results,
            channel_filter=request.channel_filter,
            category_filter=request.category_filter,
        )

        return [SearchResult(**result) for result in results]

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/search/recent", response_model=List[Dict[str, Any]])
async def get_recent_videos(
    n_results: int = Query(20, description="Number of recent videos to return"),
    channel_filter: Optional[str] = Query(None, description="Filter by channel name"),
):
    """Get most recently processed videos"""
    try:
        results = vector_db.get_recent_videos(
            n_results=n_results, channel_filter=channel_filter
        )
        return results

    except Exception as e:
        logger.error(f"Recent videos error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent videos")


@app.get("/search/by-channel/{channel_name}")
async def search_by_channel(
    channel_name: str,
    query: Optional[str] = Query(
        None, description="Optional search query within channel"
    ),
    n_results: int = Query(10, description="Number of results"),
):
    """Search videos from a specific channel"""
    try:
        if query:
            # Semantic search within channel
            results = vector_db.search_similar(
                query=query, n_results=n_results, channel_filter=channel_name
            )
        else:
            # Recent videos from channel
            results = vector_db.get_recent_videos(
                n_results=n_results, channel_filter=channel_name
            )

        return results

    except Exception as e:
        logger.error(f"Channel search error: {e}")
        raise HTTPException(status_code=500, detail="Channel search failed")


# Database stats
@app.get("/stats")
async def get_database_stats():
    """Get vector database statistics"""
    try:
        stats = vector_db.get_stats()
        return {
            "total_documents": stats.get("total_documents", 0),
            "channel_distribution": stats.get("channel_distribution", {}),
            "last_updated": stats.get("last_updated", ""),
        }

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")


@app.get("/stats/supadata")
async def get_supadata_stats():
    """Get Supadata API rate limiting statistics"""
    try:
        rate_limiter = get_rate_limiter()
        stats = rate_limiter.get_stats()
        return {
            "status": "active",
            "rate_limiting": stats,
            "optimization": {
                "max_chunk_size": int(os.getenv("SUPADATA_MAX_CHUNK_SIZE", "32000")),
                "default_mode": os.getenv("SUPADATA_DEFAULT_MODE", "native"),
                "fallback_mode": os.getenv("SUPADATA_FALLBACK_MODE", "auto")
            }
        }
    except Exception as e:
        logger.error(f"Supadata stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Supadata stats")


# Channel information (read-only)
@app.get("/channels", response_model=List[Dict[str, Any]])
async def get_channels():
    """Get all enabled channels"""
    try:
        channels = creator_manager.get_enabled_channels()
        return [
            {
                "channel_name": channel.channel_name,
                "channel_url": channel.channel_url,
                "presenters": channel.presenters,
                "category": channel.category,
            }
            for channel in channels
        ]
    except Exception as e:
        logger.error(f"Channels error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load channels")


# Hierarchical chunk search endpoints
@app.post("/search/chunks")
async def search_chunks(
    query: str,
    channel_filter: Optional[str] = None,
    video_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = Query(10, description="Number of results"),
    score_threshold: float = Query(0.7, description="Minimum similarity score"),
):
    """Search transcript chunks with hierarchical filtering"""
    try:
        if hasattr(vector_db, "search_chunks"):
            results = vector_db.search_chunks(
                query=query,
                channel_filter=channel_filter,
                video_filter=video_filter,
                category_filter=category_filter,
                limit=limit,
                score_threshold=score_threshold,
            )
            return {"query": query, "results": results, "total_found": len(results)}
        else:
            raise HTTPException(status_code=501, detail="Chunk search not available")
    except Exception as e:
        logger.error(f"Chunk search error: {e}")
        raise HTTPException(status_code=500, detail="Chunk search failed")


@app.get("/video/{video_id}/chunks")
async def get_video_chunks(
    video_id: str,
    channel_id: Optional[str] = Query(None, description="Channel ID for filtering"),
):
    """Get all chunks for a specific video"""
    try:
        if hasattr(vector_db, "get_video_chunks"):
            chunks = vector_db.get_video_chunks(video_id, channel_id)
            return {"video_id": video_id, "chunks": chunks, "total_chunks": len(chunks)}
        else:
            raise HTTPException(status_code=501, detail="Video chunks not available")
    except Exception as e:
        logger.error(f"Video chunks error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video chunks")


@app.get("/channel/{channel_id}/videos")
async def get_channel_videos(channel_id: str):
    """Get all videos for a channel (from chunk metadata)"""
    try:
        if hasattr(vector_db, "get_channel_videos"):
            videos = vector_db.get_channel_videos(channel_id)
            return {
                "channel_id": channel_id,
                "videos": videos,
                "total_videos": len(videos),
            }
        else:
            raise HTTPException(status_code=501, detail="Channel videos not available")
    except Exception as e:
        logger.error(f"Channel videos error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get channel videos")


# Enhanced health check endpoints
@app.get("/health/full")
async def full_health_check():
    """Comprehensive health check with all component status"""
    try:
        health_results = await health_monitor.run_all_health_checks()
        return health_results
    except Exception as e:
        logger.error(f"Full health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/health/summary")
async def health_summary():
    """Quick health summary from last checks"""
    try:
        summary = health_monitor.get_health_summary()
        return summary
    except Exception as e:
        logger.error(f"Health summary error: {e}")
        raise HTTPException(status_code=500, detail="Health summary failed")


# Initialize Groq client
groq_client = None
try:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        groq_client = Groq(api_key=groq_api_key)
        logger.info("✅ Groq client initialized successfully")
    else:
        logger.warning("⚠️ GROQ_API_KEY not found - insights endpoint will be unavailable")
except Exception as e:
    logger.error(f"❌ Failed to initialize Groq client: {e}")
    groq_client = None


def build_timestamped_transcript_from_chunks(chunks: List[Dict[str, Any]]) -> str:
    """Build a complete timestamped transcript from chunks"""
    transcript_lines = []
    
    for chunk in chunks:
        start_seconds = chunk["start_ms"] // 1000
        start_minutes = start_seconds // 60
        start_secs_remainder = start_seconds % 60
        
        timestamp = f"[{start_minutes}:{start_secs_remainder:02d}]"
        transcript_lines.append(f"{timestamp} {chunk['chunk_text']}")
    
    return "\n\n".join(transcript_lines)


def generate_financial_insights_prompt(transcript: str, channel_name: str, video_title: str) -> str:
    """Generate the financial insights prompt for Groq"""
    return f"""You are RobinCortex, an advanced AI financial analyst. Analyze this YouTube video transcript from {channel_name} titled "{video_title}".

TRANSCRIPT:
{transcript}

Generate a comprehensive financial analysis in JSON format with these exact fields:

{{
    "title": "Compelling, actionable title summarizing the main investment theme",
    "tickers": [
        {{"symbol": "TICKER", "context": "Why mentioned and relevance", "sentiment": "bullish/bearish/neutral", "timestamp_reference": "[MM:SS] format"}},
    ],
    "key_metrics": [
        {{"metric": "Specific financial metric", "value": "Actual number/percentage", "context": "What it means", "timestamp_reference": "[MM:SS] format"}},
    ],
    "market_insights": [
        {{"insight": "Actionable market insight", "category": "trend/opportunity/risk/catalyst", "timestamp_reference": "[MM:SS] format", "confidence": "high/medium/low"}},
    ],
    "investment_thesis": "2-3 sentence summary of the main investment argument",
    "sentiment_analysis": {{"overall": "bullish/bearish/neutral", "confidence": "high/medium/low", "key_drivers": ["list", "of", "factors"]}},
    "timestamps": [
        {{"time": "[MM:SS]", "topic": "Key topic discussed", "importance": "high/medium/low"}},
    ]
}}

Focus on:
- Extracting ALL stock tickers and companies mentioned
- Identifying specific financial metrics, earnings, valuations
- Market trends, catalysts, and investment opportunities
- Sentiment analysis of each mention
- Timestamped key moments for easy navigation

Be precise, factual, and focus on actionable investment intelligence."""


@app.get("/insights/{video_id}", response_model=InsightResult)
async def generate_insights(
    video_id: str,
    channel_id: Optional[str] = Query(None, description="Optional channel ID for filtering")
):
    """Generate RobinCortex-style financial insights for a video using Groq"""
    if not groq_client:
        raise HTTPException(status_code=503, detail="Groq API not available - check GROQ_API_KEY")
    
    try:
        # Get video chunks from vector database
        chunks = vector_db.get_video_chunks(video_id, channel_id)
        
        if not chunks:
            raise HTTPException(status_code=404, detail=f"No transcript chunks found for video {video_id}")
        
        # Sort chunks by index to maintain order
        chunks.sort(key=lambda x: x["chunk_index"])
        
        # Get video metadata from first chunk
        video_title = chunks[0]["metadata"].get("video_title", f"Video {video_id}")
        channel_name = chunks[0]["metadata"].get("channel_name", "Unknown Channel")
        
        logger.info(f"🎯 Generating insights for '{video_title}' from {channel_name} ({len(chunks)} chunks)")
        
        # Build complete transcript with timestamps (limit to avoid token limits)
        limited_chunks = chunks[:15]  # Limit to first 15 chunks to stay within token limits
        transcript = build_timestamped_transcript_from_chunks(limited_chunks)
        
        # Truncate transcript if too long (rough estimate: 1 token ≈ 4 characters)
        max_chars = 12000  # ~3000 tokens for transcript, leaving room for prompt
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "\n[...transcript truncated due to length...]"
        
        # Generate insights prompt
        prompt = generate_financial_insights_prompt(transcript, channel_name, video_title)
        
        logger.info(f"📊 Analyzing {len(transcript)} characters with Groq GPT-OSS 120B...")
        
        # Call Groq API with streaming
        completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="openai/gpt-oss-120b",  # Using the original GPT-OSS model
            temperature=0.3,
            max_tokens=4000,
            top_p=1,
            stream=False  # Disable streaming for API endpoint
        )
        
        # Extract and parse JSON response
        response_text = completion.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                insights = json.loads(json_text)
            else:
                # Fallback: treat entire response as text
                insights = {
                    "title": "Financial Analysis Complete",
                    "raw_analysis": response_text,
                    "error": "Could not parse structured JSON response"
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            insights = {
                "title": "Financial Analysis Complete",
                "raw_analysis": response_text,
                "parse_error": str(e)
            }
        
        # Add metadata
        insights["video_metadata"] = {
            "video_id": video_id,
            "channel_name": channel_name,
            "video_title": video_title,
            "total_chunks": len(chunks),
            "transcript_length": len(transcript)
        }
        
        result = InsightResult(
            video_id=video_id,
            video_title=video_title,
            channel_name=channel_name,
            insights=insights,
            generated_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"✅ Generated insights for {video_id} successfully")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insights for {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)

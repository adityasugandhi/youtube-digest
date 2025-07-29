from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict
import logging
import asyncio
import sys
import os

# Add shared schemas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../shared'))
from schemas.common import StreamInfo

from app.services.youtube_client import YouTubeClient
from app.api.dependencies import get_youtube_client, rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/channel/{channel_identifier}/completed")
async def get_channel_completed_streams(
    channel_identifier: str,
    max_results: int = Query(default=10, le=50),
    include_transcripts: bool = Query(default=False),
    youtube_client: YouTubeClient = Depends(get_youtube_client),
    _: None = Depends(rate_limit)
):
    """
    Get completed live streams from a channel with optional transcripts
    
    Args:
        channel_identifier: Either a channel ID (UCxxxxxxxxx) or handle (@username)
        max_results: Maximum number of streams to return (1-50)
        include_transcripts: Whether to include transcript data
    """
    
    try:
        # Determine if this is a channel ID or handle
        if channel_identifier.startswith('UC') and len(channel_identifier) == 24:
            # Already a channel ID
            channel_id = channel_identifier
        else:
            # Handle - resolve to channel ID
            logger.info(f"Resolving handle '{channel_identifier}' to channel ID")
            channel_id = await youtube_client.resolve_handle_to_channel_id(channel_identifier)
            
            if not channel_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not resolve channel handle '{channel_identifier}' to channel ID"
                )
        
        # Get completed streams
        streams = await youtube_client.get_completed_live_streams(
            channel_id, max_results
        )
        
        if not streams:
            return {
                "channel_identifier": channel_identifier,
                "channel_id": channel_id,
                "streams": [],
                "count": 0,
                "message": "No live streams found for this channel"
            }
        
        if not include_transcripts:
            return {
                "channel_identifier": channel_identifier,
                "channel_id": channel_id,
                "streams": [stream.model_dump() for stream in streams],
                "count": len(streams)
            }
        
        # Extract transcripts for all streams
        video_ids = [stream.video_id for stream in streams]
        logger.info(f"Extracting transcripts for {len(video_ids)} videos")
        
        transcripts = await youtube_client.batch_extract_transcripts(
            video_ids,
            concurrent_limit=5
        )
        
        # Combine streams with transcripts
        enriched_streams = []
        for stream in streams:
            stream_dict = stream.model_dump()
            transcript = transcripts.get(stream.video_id)
            stream_dict["transcript"] = transcript
            stream_dict["has_transcript"] = transcript is not None
            
            # Add transcript stats if available
            if transcript:
                stream_dict["transcript_stats"] = {
                    "segment_count": len(transcript),
                    "total_duration": transcript[-1].end if transcript else 0,
                    "total_words": sum(len(seg.text.split()) for seg in transcript)
                }
            
            enriched_streams.append(stream_dict)
        
        transcripts_available = sum(1 for s in enriched_streams if s["has_transcript"])
        
        return {
            "channel_identifier": channel_identifier,
            "channel_id": channel_id,
            "streams": enriched_streams,
            "count": len(enriched_streams),
            "transcripts_available": transcripts_available,
            "transcript_success_rate": f"{(transcripts_available/len(streams)*100):.1f}%" if streams else "0%"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching channel streams for '{channel_identifier}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/resolve/{handle}")
async def resolve_channel_handle(
    handle: str,
    youtube_client: YouTubeClient = Depends(get_youtube_client),
    _: None = Depends(rate_limit)
):
    """
    Resolve a YouTube handle to channel ID
    
    Args:
        handle: YouTube handle (e.g., "@amitinvesting" or "amitinvesting")
    
    Returns:
        Channel ID and basic channel information
    """
    
    try:
        # Resolve handle to channel ID
        channel_id = await youtube_client.resolve_handle_to_channel_id(handle)
        
        if not channel_id:
            raise HTTPException(
                status_code=404,
                detail=f"Could not resolve handle '{handle}' to channel ID"
            )
        
        # Get basic channel information
        channel_response = await asyncio.to_thread(
            youtube_client.youtube.channels().list,
            part='snippet,statistics',
            id=channel_id
        )
        
        if not channel_response.get('items'):
            raise HTTPException(
                status_code=404,
                detail=f"Channel not found for ID '{channel_id}'"
            )
        
        channel_data = channel_response['items'][0]
        snippet = channel_data['snippet']
        stats = channel_data['statistics']
        
        return {
            "handle": handle,
            "channel_id": channel_id,
            "channel_info": {
                "title": snippet['title'],
                "description": snippet['description'][:200] + "..." if len(snippet['description']) > 200 else snippet['description'],
                "custom_url": snippet.get('customUrl', ''),
                "published_at": snippet['publishedAt'],
                "subscriber_count": int(stats.get('subscriberCount', 0)),
                "video_count": int(stats.get('videoCount', 0)),
                "view_count": int(stats.get('viewCount', 0))
            },
            "urls": {
                "channel": f"https://www.youtube.com/channel/{channel_id}",
                "handle": f"https://www.youtube.com/{handle}" if handle.startswith('@') else f"https://www.youtube.com/@{handle}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving handle '{handle}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{video_id}/info")
async def get_stream_info(
    video_id: str,
    youtube_client: YouTubeClient = Depends(get_youtube_client),
    _: None = Depends(rate_limit)
):
    """Get detailed information about a specific video/stream"""
    
    try:
        # Get video details
        video_response = await asyncio.to_thread(
            youtube_client.youtube.videos().list,
            part='snippet,liveStreamingDetails,statistics,contentDetails',
            id=video_id
        )
        
        if not video_response.get('items'):
            raise HTTPException(
                status_code=404,
                detail=f"Video not found: {video_id}"
            )
        
        video_data = video_response['items'][0]
        snippet = video_data['snippet']
        stats = video_data['statistics']
        content = video_data['contentDetails']
        
        result = {
            "video_id": video_id,
            "title": snippet['title'],
            "description": snippet['description'][:300] + "..." if len(snippet['description']) > 300 else snippet['description'],
            "channel_id": snippet['channelId'],
            "channel_title": snippet['channelTitle'],
            "published_at": snippet['publishedAt'],
            "duration": content.get('duration'),
            "view_count": int(stats.get('viewCount', 0)),
            "like_count": int(stats.get('likeCount', 0)),
            "comment_count": int(stats.get('commentCount', 0)),
            "is_live_stream": 'liveStreamingDetails' in video_data,
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }
        
        # Add live streaming details if available
        if 'liveStreamingDetails' in video_data:
            live_details = video_data['liveStreamingDetails']
            result["live_streaming_details"] = {
                "actual_start_time": live_details.get('actualStartTime'),
                "actual_end_time": live_details.get('actualEndTime'),
                "scheduled_start_time": live_details.get('scheduledStartTime'),
                "concurrent_viewers": live_details.get('concurrentViewers')
            }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching video info for {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
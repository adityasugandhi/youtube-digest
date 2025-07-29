from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict
import logging
import sys
import os

# Add shared schemas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../shared'))
from schemas.common import (
    TranscriptResponse, 
    BatchTranscriptRequest, 
    BatchTranscriptResponse,
    StreamInfo
)

from app.services.youtube_client import YouTubeClient
from app.api.dependencies import get_youtube_client, rate_limit
from app.utils.cache import cache_result, get_cached_result

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{video_id}", response_model=TranscriptResponse)
async def get_transcript(
    video_id: str,
    youtube_client: YouTubeClient = Depends(get_youtube_client),
    _: None = Depends(rate_limit)
):
    """Extract transcript from a single YouTube video"""
    
    # Check cache first
    cached_result = await get_cached_result(f"transcript:{video_id}")
    if cached_result:
        return cached_result
    
    try:
        transcript = await youtube_client.extract_transcript(video_id)
        
        if not transcript:
            raise HTTPException(
                status_code=404, 
                detail=f"No transcript available for video {video_id}"
            )
        
        response = TranscriptResponse(
            video_id=video_id,
            transcript=transcript,
            segment_count=len(transcript),
            total_duration=transcript[-1].end if transcript else 0,
            language="en",
            is_auto_generated=True  # Detect this properly
        )
        
        # Cache the result
        await cache_result(f"transcript:{video_id}", response, ttl=3600)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing transcript request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch", response_model=BatchTranscriptResponse)
async def get_batch_transcripts(
    request: BatchTranscriptRequest,
    background_tasks: BackgroundTasks,
    youtube_client: YouTubeClient = Depends(get_youtube_client),
    _: None = Depends(rate_limit)
):
    """Extract transcripts from multiple videos concurrently"""
    
    if len(request.video_ids) > 20:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 20 videos per batch request"
        )
    
    try:
        # Process batch extraction
        transcripts = await youtube_client.batch_extract_transcripts(
            request.video_ids,
            concurrent_limit=request.concurrent_limit or 5
        )
        
        # Prepare response
        successful = []
        failed = []
        
        for video_id, transcript in transcripts.items():
            if transcript is not None:
                successful.append(TranscriptResponse(
                    video_id=video_id,
                    transcript=transcript,
                    segment_count=len(transcript),
                    total_duration=transcript[-1].end if transcript else 0,
                    language="en",
                    is_auto_generated=True
                ))
                
                # Cache successful results in background
                background_tasks.add_task(
                    cache_result, 
                    f"transcript:{video_id}", 
                    successful[-1], 
                    3600
                )
            else:
                failed.append({
                    "video_id": video_id,
                    "error": "Transcript not available"
                })
        
        return BatchTranscriptResponse(
            successful=successful,
            failed=failed,
            total_requested=len(request.video_ids),
            successful_count=len(successful),
            failed_count=len(failed)
        )
        
    except Exception as e:
        logger.error(f"Error processing batch transcript request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
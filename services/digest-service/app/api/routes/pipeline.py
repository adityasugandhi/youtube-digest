from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict
import logging
import aiohttp
import asyncio
import sys
import os

# Add shared schemas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../shared'))
from schemas.common import DigestRequest, DigestResponse

from app.services.digest_generator import RobinhoodDigestGenerator
from app.api.dependencies import get_digest_generator, rate_limit
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/process-stream/{video_id}", response_model=DigestResponse)
async def process_stream_to_digest(
    video_id: str,
    channel_name: Optional[str] = None,
    focus_areas: Optional[str] = None,
    digest_generator: RobinhoodDigestGenerator = Depends(get_digest_generator),
    _: None = Depends(rate_limit)
):
    """
    End-to-end pipeline: Extract transcript from video and generate digest
    
    This endpoint:
    1. Calls the YouTube service to extract transcript
    2. Processes the transcript with AI to generate a financial digest
    3. Returns the complete digest
    """
    
    try:
        logger.info(f"Starting end-to-end processing for video {video_id}")
        
        # Step 1: Extract transcript from YouTube service
        transcript_data = await _fetch_transcript_from_youtube_service(video_id)
        
        if not transcript_data:
            raise HTTPException(
                status_code=404,
                detail=f"Could not extract transcript for video {video_id}"
            )
        
        logger.info(f"Transcript extracted: {transcript_data['segment_count']} segments")
        
        # Step 2: Prepare transcript text
        transcript_text = ' '.join([
            segment['text'] for segment in transcript_data['transcript']
        ])
        
        # Step 3: Get video metadata from YouTube service
        video_metadata = await _fetch_video_metadata(video_id)
        
        # Step 4: Prepare digest request
        digest_request = DigestRequest(
            video_id=video_id,
            transcript=transcript_text,
            metadata={
                'channel_name': channel_name or video_metadata.get('channel_title', 'Unknown Channel'),
                'video_title': video_metadata.get('title', 'Live Stream'),
                'stream_date': video_metadata.get('published_at', 'Unknown'),
                'duration': transcript_data.get('total_duration', 0),
                'view_count': video_metadata.get('view_count', 0),
                'transcript_segments': transcript_data['segment_count'],
                'transcript_words': sum(len(seg['text'].split()) for seg in transcript_data['transcript'])
            },
            focus_areas=focus_areas or "Financial market analysis, investment insights, and trading opportunities",
            ai_providers=["groq"]
        )
        
        # Step 5: Generate digest
        logger.info(f"Generating digest for {len(transcript_text)} characters of transcript")
        digest = await digest_generator.generate_digest(digest_request)
        
        logger.info(f"Digest generated successfully with quality score {digest.quality_score}")
        
        return digest
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in end-to-end processing for video {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/process-channel/{channel_identifier}", response_model=List[DigestResponse])
async def process_channel_streams(
    channel_identifier: str,
    max_streams: int = 3,
    focus_areas: Optional[str] = None,
    digest_generator: RobinhoodDigestGenerator = Depends(get_digest_generator),
    _: None = Depends(rate_limit)
):
    """
    Process multiple streams from a channel and generate digests
    
    This endpoint:
    1. Gets recent live streams from the channel
    2. Extracts transcripts for each stream
    3. Generates financial digests for all streams
    4. Returns list of digests
    """
    
    try:
        logger.info(f"Processing channel {channel_identifier} for {max_streams} streams")
        
        # Step 1: Get streams with transcripts from YouTube service
        streams_data = await _fetch_channel_streams(channel_identifier, max_streams)
        
        if not streams_data or not streams_data.get('streams'):
            raise HTTPException(
                status_code=404,
                detail=f"No streams found for channel {channel_identifier}"
            )
        
        # Step 2: Process each stream that has a transcript
        digest_requests = []
        for stream in streams_data['streams']:
            if stream.get('has_transcript') and stream.get('transcript'):
                
                # Prepare transcript text
                transcript_text = ' '.join([
                    segment['text'] for segment in stream['transcript']
                ])
                
                # Create digest request
                digest_request = DigestRequest(
                    video_id=stream['video_id'],
                    transcript=transcript_text,
                    metadata={
                        'channel_name': stream['channel_title'],
                        'video_title': stream['title'],
                        'stream_date': stream['published_at'],
                        'duration': stream.get('duration', 'Unknown'),
                        'view_count': stream['view_count'],
                        'transcript_segments': len(stream['transcript']),
                        'transcript_words': sum(len(seg['text'].split()) for seg in stream['transcript'])
                    },
                    focus_areas=focus_areas or "Financial market analysis, investment insights, and trading opportunities",
                    ai_providers=["groq"]
                )
                
                digest_requests.append(digest_request)
        
        if not digest_requests:
            raise HTTPException(
                status_code=404,
                detail=f"No streams with transcripts found for channel {channel_identifier}"
            )
        
        # Step 3: Generate digests for all streams
        logger.info(f"Generating {len(digest_requests)} digests")
        digests = await digest_generator.batch_generate_digests(digest_requests)
        
        successful_digests = [d for d in digests if not d.error]
        logger.info(f"Generated {len(successful_digests)} successful digests")
        
        return digests
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing channel {channel_identifier}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _fetch_transcript_from_youtube_service(video_id: str) -> Optional[Dict]:
    """Fetch transcript from YouTube service"""
    
    youtube_service_url = "http://localhost:8001"  # In production, use service discovery
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{youtube_service_url}/api/v1/transcripts/{video_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to fetch transcript for {video_id}: HTTP {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error fetching transcript for {video_id}: {e}")
        return None


async def _fetch_video_metadata(video_id: str) -> Dict:
    """Fetch video metadata from YouTube service"""
    
    youtube_service_url = "http://localhost:8001"
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{youtube_service_url}/api/v1/streams/{video_id}/info"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to fetch metadata for {video_id}: HTTP {response.status}")
                    return {}
                    
    except Exception as e:
        logger.error(f"Error fetching metadata for {video_id}: {e}")
        return {}


async def _fetch_channel_streams(channel_identifier: str, max_results: int) -> Optional[Dict]:
    """Fetch channel streams with transcripts from YouTube service"""
    
    youtube_service_url = "http://localhost:8001"
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{youtube_service_url}/api/v1/streams/channel/{channel_identifier}/completed"
            params = {
                "max_results": max_results,
                "include_transcripts": True
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to fetch streams for {channel_identifier}: HTTP {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error fetching streams for {channel_identifier}: {e}")
        return None
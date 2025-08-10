"""
YouTube transcript extraction and summarization pipeline with exponential backoff retry
"""

import os
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import google.generativeai as genai
from supadata import Supadata, SupadataError
import time
import requests
from dotenv import load_dotenv

# Load environment variables from parent directory
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from models import YouTubeChannel, VideoMetadata, ProcessedVideo
from retry_utils import supabase_data_retry, supabase_api_retry, gemini_api_retry
from supadata_rate_limiter import rate_limited_supadata_call, get_rate_limiter

logger = logging.getLogger(__name__)


class SupadataClient:
    """Supadata client for video data management"""

    def __init__(self):
        api_key = os.getenv("SUPADATA_API_KEY")

        if not api_key:
            raise ValueError("SUPADATA_API_KEY must be set")

        self.supadata = Supadata(api_key=api_key)

    @supabase_api_retry
    def get_recent_videos(
        self, channel_id: str, max_results: int = 10, hours_back: int = 25
    ) -> List[VideoMetadata]:
        """Get recent videos from a channel using Supadata"""
        try:
            # Get channel videos (try both live and regular videos)
            videos = []

            # Try to get live videos first
            try:
                channel_videos = self.supadata.youtube.channel.videos(
                    id=channel_id, type="live", limit=max_results
                )
                video_ids = getattr(channel_videos, "live_ids", [])[:max_results]
                logger.info(
                    f"Found {len(video_ids)} live videos for channel {channel_id}"
                )
            except Exception as live_error:
                logger.warning(f"Failed to get live videos: {live_error}")
                video_ids = []

            # If no live videos, try regular videos
            if not video_ids:
                try:
                    channel_videos = self.supadata.youtube.channel.videos(
                        id=channel_id, limit=max_results
                    )
                    # Handle different response formats
                    if hasattr(channel_videos, "video_ids"):
                        video_ids = channel_videos.video_ids[:max_results]
                    elif hasattr(channel_videos, "ids"):
                        video_ids = channel_videos.ids[:max_results]
                    else:
                        # Try to extract from response object
                        video_ids = []
                        for attr in ["live_ids", "video_ids", "ids"]:
                            if hasattr(channel_videos, attr):
                                video_ids = getattr(channel_videos, attr)[:max_results]
                                break
                    logger.info(
                        f"Found {len(video_ids)} regular videos for channel {channel_id}"
                    )
                except Exception as regular_error:
                    logger.warning(f"Failed to get regular videos: {regular_error}")
                    video_ids = []

            # Process videos
            for video_id in video_ids:
                try:
                    # Get video metadata
                    video_data = self.supadata.youtube.video(id=video_id)

                    # Convert to VideoMetadata - handle both dict and object responses
                    if isinstance(video_data, dict):
                        video_metadata = VideoMetadata(
                            video_id=video_data.get("id", video_id),
                            title=video_data.get("title", f"Video {video_id}"),
                            channel_name=video_data.get("channel", {}).get(
                                "name", "Unknown"
                            ),
                            channel_url=f"https://www.youtube.com/channel/{video_data.get('channel', {}).get('id', channel_id)}",
                            presenters=[],  # Will be filled from channel config
                            publish_time=video_data.get(
                                "uploaded_date", datetime.now().isoformat()
                            ),
                            video_url=f"https://www.youtube.com/watch?v={video_id}",
                            duration=video_data.get("duration", 0),
                            view_count=video_data.get("view_count", 0),
                        )
                    else:
                        video_metadata = VideoMetadata(
                            video_id=video_data.id,
                            title=video_data.title,
                            channel_name=(
                                video_data.channel.get("name")
                                if isinstance(video_data.channel, dict)
                                else video_data.channel.name
                            ),
                            channel_url=f"https://www.youtube.com/channel/{video_data.channel.get('id') if isinstance(video_data.channel, dict) else video_data.channel.id}",
                            presenters=[],  # Will be filled from channel config
                            publish_time=video_data.uploaded_date,
                            video_url=f"https://www.youtube.com/watch?v={video_data.id}",
                            duration=video_data.duration,
                            view_count=video_data.view_count,
                        )
                    videos.append(video_metadata)

                    # Rate limiting
                    time.sleep(0.5)

                except Exception as video_error:
                    logger.warning(f"Error getting video {video_id}: {video_error}")
                    continue

            logger.info(
                f"Found {len(videos)} recent live videos for channel {channel_id}"
            )
            return videos

        except SupadataError as e:
            logger.error(f"Supadata API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching videos from Supadata: {e}")
            return []


class TranscriptExtractor:
    """YouTube transcript extraction using multiple methods with caching"""

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Initialize vector database for transcript caching
        from qdrant_vector_db import QdrantVectorDB

        self.vector_db = QdrantVectorDB()

    def extract_transcript(self, video_id: str) -> Optional[str]:
        """Extract transcript from YouTube video using Supadata API"""

        # Try Supadata API
        transcript = self._extract_supadata_transcript(video_id)
        if transcript:
            return transcript

        # No more fallbacks - return None if Supabase fails
        logger.warning(f"No transcript available for {video_id} from any source")
        return None

    def _extract_supadata_transcript(self, video_id: str) -> Optional[str]:
        """Extract transcript using Supadata API with maximum chunk size optimization"""
        try:
            api_key = os.getenv("SUPADATA_API_KEY")

            if not api_key:
                logger.error("SUPADATA_API_KEY not found")
                return None

            supadata = Supadata(api_key=api_key)

            # Use maximum chunk size to minimize API calls
            max_chunk_size = int(os.getenv("SUPADATA_MAX_CHUNK_SIZE", "32000"))
            default_mode = os.getenv("SUPADATA_DEFAULT_MODE", "native")
            fallback_mode = os.getenv("SUPADATA_FALLBACK_MODE", "auto")

            logger.info(
                f"Requesting plain text transcript for {video_id} with chunk_size={max_chunk_size}"
            )

            # Apply rate limiting before API call
            rate_limiter = get_rate_limiter()

            # Try default mode first for best accuracy
            try:
                rate_limiter.wait_if_needed()
                transcript_response = supadata.youtube.transcript(
                    video_id=video_id,
                    text=True,  # Plain text for this method
                    mode=default_mode,
                    chunk_size=max_chunk_size,
                )

                if transcript_response and transcript_response.content:
                    transcript_text = transcript_response.content
                    logger.info(
                        f"✅ {default_mode.title()} mode plain text transcript for {video_id} ({len(transcript_text)} chars)"
                    )
                    return transcript_text

            except SupadataError as default_error:
                logger.warning(
                    f"{default_mode.title()} mode failed for plain text {video_id}: {default_error}"
                )

                # Fallback to alternative mode (rate limited)
                rate_limiter.wait_if_needed()
                transcript_response = supadata.youtube.transcript(
                    video_id=video_id,
                    text=True,
                    mode=fallback_mode,
                    chunk_size=max_chunk_size,
                )

                if transcript_response and transcript_response.content:
                    transcript_text = transcript_response.content
                    logger.info(
                        f"✅ {fallback_mode.title()} mode plain text transcript for {video_id} ({len(transcript_text)} chars)"
                    )
                    return transcript_text

            logger.debug(f"No transcript content found for {video_id}")
            return None

        except SupadataError as e:
            logger.debug(f"Supadata transcript extraction failed for {video_id}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Supadata transcript extraction error for {video_id}: {e}")
            return None

    def _get_supadata_transcript_response(
        self, video_id: str, max_chunk_size: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get raw Supadata transcript response optimized for minimum API calls"""
        try:
            api_key = os.getenv("SUPADATA_API_KEY")

            if not api_key:
                logger.error("SUPADATA_API_KEY not found")
                return None

            supadata = Supadata(api_key=api_key)

            # Use configurable maximum chunk size to minimize API calls
            optimal_chunk_size = max_chunk_size or int(
                os.getenv("SUPADATA_MAX_CHUNK_SIZE", "32000")
            )
            default_mode = os.getenv("SUPADATA_DEFAULT_MODE", "native")
            fallback_mode = os.getenv("SUPADATA_FALLBACK_MODE", "auto")

            logger.info(
                f"Requesting structured transcript for {video_id} with chunk_size={optimal_chunk_size}"
            )

            # Apply rate limiting
            rate_limiter = get_rate_limiter()

            # Try default mode first (configurable)
            try:
                rate_limiter.wait_if_needed()
                transcript_response = supadata.youtube.transcript(
                    video_id=video_id,
                    text=False,  # Get structured data with timestamps
                    mode=default_mode,  # Configurable primary mode
                    chunk_size=optimal_chunk_size,  # Maximum size to minimize requests
                )

                logger.info(
                    f"✅ {default_mode.title()} mode structured transcript retrieved for {video_id}"
                )
                return transcript_response

            except SupadataError as default_error:
                logger.warning(
                    f"{default_mode.title()} mode failed for {video_id}: {default_error}"
                )

                # Fallback to alternative mode (rate limited)
                logger.info(f"Falling back to {fallback_mode} mode for {video_id}")
                rate_limiter.wait_if_needed()
                transcript_response = supadata.youtube.transcript(
                    video_id=video_id,
                    text=False,
                    mode=fallback_mode,  # Configurable fallback mode
                    chunk_size=optimal_chunk_size,
                )

                logger.info(
                    f"✅ {fallback_mode.title()} mode structured transcript retrieved for {video_id}"
                )
                return transcript_response

        except SupadataError as e:
            logger.error(f"Supadata transcript failed for {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Supadata transcript error for {video_id}: {e}")
            return None

    @supabase_api_retry
    def _extract_supabase_transcript(self, video_id: str) -> Optional[str]:
        """Extract transcript using Supabase YouTube API with exponential backoff retry"""
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        api_key = os.getenv("SUPABASE_YOUTUBE_API")

        if not api_key:
            logger.error("SUPABASE_YOUTUBE_API key not found")
            return None

        # Call Supabase API
        response = requests.get(
            f"https://api.supadata.ai/v1/transcript?url={video_url}",
            headers={"x-api-key": api_key},
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()

            if "content" in data and data["content"]:
                # Extract text from content array
                transcript_text = " ".join([item["text"] for item in data["content"]])
                logger.info(
                    f"Extracted Supabase transcript for {video_id} ({len(transcript_text)} characters)"
                )
                return transcript_text.strip()
            else:
                logger.warning(f"No content in Supabase response for {video_id}")
                return None
        else:
            # Raise an exception for retryable status codes
            response.raise_for_status()
            logger.warning(f"Supabase API error {response.status_code} for {video_id}")
            return None


class GeminiSummarizer:
    """Gemini-based summarization"""

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def create_summary_prompt(
        self,
        transcript: str,
        channel_name: str,
        presenters: List[str],
        category: str = "investing",
    ) -> str:
        """Create a summary prompt tailored for financial content"""
        presenters_str = ", ".join(presenters) if presenters else "the presenter"

        prompt = f"""
You are an AI language model designed to process YouTube video transcripts from {channel_name} by {presenters_str}.

Given the following transcript, extract and summarize the main points, key topics, important timestamps, as well as any stock ticker symbols (e.g., AAPL, TSLA, MSFT) or financial entities mentioned.

Format your output clearly with bullet points or numbered lists.

**REQUIREMENTS:**
1. Provide a high-level summary of the video.
2. List out the main topics covered, each with a brief explanation and relevant timestamps (if available).
3. Extract all stock ticker symbols or company names referenced during the video, listing each one with the context or related sentence from the transcript and its timestamp.
4. Highlight any notable finance quotes, facts, or actionable investment insights reported.

**INPUT TRANSCRIPT:**
{transcript}

**FORMAT YOUR RESPONSE AS:**

## High-Level Summary
[2-3 sentence overview of the video's main theme and purpose]

## Main Topics Covered
1. **Topic 1** - [Brief explanation with timestamp if available]
2. **Topic 2** - [Brief explanation with timestamp if available]
3. **Topic 3** - [Brief explanation with timestamp if available]

## Stock Tickers & Companies Mentioned
• **TICKER/Company** - [Context from transcript with timestamp]
• **TICKER/Company** - [Context from transcript with timestamp]

## Notable Quotes & Investment Insights
• [Key actionable insight or quote with timestamp]
• [Important financial fact or recommendation with timestamp]
• [Contrarian view or unique perspective with timestamp]

Focus on financial intelligence that matters to investors and traders.
"""
        return prompt

    @gemini_api_retry
    def summarize_transcript(
        self, transcript: str, metadata: VideoMetadata
    ) -> Optional[str]:
        """Summarize transcript using Gemini with exponential backoff retry"""
        # Check transcript length - truncate if too long
        max_chars = 50000  # Gemini context limit consideration
        if len(transcript) > max_chars:
            logger.warning(f"Transcript too long ({len(transcript)} chars), truncating")
            transcript = transcript[:max_chars] + "... [truncated]"

        # Create prompt
        prompt = self.create_summary_prompt(
            transcript=transcript,
            channel_name=metadata.channel_name,
            presenters=metadata.presenters,
            category=metadata.category,
        )

        # Generate summary
        response = self.model.generate_content(prompt)
        summary = response.text.strip()

        logger.info(
            f"Generated summary for {metadata.video_id} ({len(summary)} characters)"
        )
        return summary

    def chunk_and_summarize(
        self, transcript: str, metadata: VideoMetadata, chunk_size: int = 40000
    ) -> Optional[str]:
        """Handle very long transcripts by chunking"""
        if len(transcript) <= chunk_size:
            return self.summarize_transcript(transcript, metadata)

        try:
            # Split into chunks
            chunks = []
            for i in range(0, len(transcript), chunk_size):
                chunk = transcript[i : i + chunk_size]
                chunks.append(chunk)

            logger.info(f"Processing {len(chunks)} chunks for {metadata.video_id}")

            # Summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summary = self.summarize_transcript(chunk, metadata)
                if chunk_summary:
                    chunk_summaries.append(f"Part {i+1}: {chunk_summary}")
                time.sleep(1)  # Rate limiting

            if not chunk_summaries:
                return None

            # Combine chunk summaries
            combined_text = "\n\n".join(chunk_summaries)

            # Create final summary from chunk summaries
            final_prompt = f"""
Combine these section summaries into a single, cohesive financial analysis summary for {metadata.channel_name}:

{combined_text}

Create a unified Robinhood Cortex style summary with:
📊 [Overall compelling title]
• [Top 5 key insights, removing redundancy]

Keep the same concise, actionable format focusing on the most important financial intelligence.
"""

            response = self.model.generate_content(final_prompt)
            final_summary = response.text.strip()

            logger.info(
                f"Generated final summary from {len(chunks)} chunks for {metadata.video_id}"
            )
            return final_summary

        except Exception as e:
            logger.error(
                f"Error with chunked summarization for {metadata.video_id}: {e}"
            )
            return None


class SummarizationPipeline:
    """Main summarization pipeline"""

    def __init__(self):
        self.supadata_client = SupadataClient()
        self.transcript_extractor = TranscriptExtractor()
        self.summarizer = GeminiSummarizer()

        # Initialize vector database for storage
        from qdrant_vector_db import QdrantVectorDB

        self.vector_db = QdrantVectorDB()

    def process_channel(
        self, channel: YouTubeChannel, max_videos: int = 5
    ) -> List[ProcessedVideo]:
        """Process all recent videos from a channel and store metadata"""
        logger.info(f"Processing channel: {channel.channel_name}")

        # Get recent videos from Supadata using channel_id or resolve from channel_url
        channel_id = channel.channel_id or self._extract_channel_id_from_url(
            channel.channel_url
        )
        if not channel_id:
            logger.error(f"Could not resolve channel ID for {channel.channel_name}")
            return []

        videos = self.supadata_client.get_recent_videos(channel_id, max_videos)

        # Store channel metadata and recent video IDs
        video_ids = [video.video_id for video in videos]
        self.vector_db.store_channel_metadata(
            channel_id, channel.channel_name, channel.channel_url, video_ids
        )

        processed_videos = []
        for video_metadata in videos:
            # Add channel-specific data
            video_metadata.presenters = channel.presenters
            video_metadata.channel_url = channel.channel_url
            video_metadata.category = channel.category

            processed_video = self.process_video(video_metadata)
            if processed_video:
                processed_videos.append(processed_video)

            # Rate limiting
            time.sleep(2)

        logger.info(
            f"Successfully processed {len(processed_videos)} videos from {channel.channel_name}"
        )
        logger.info(
            f"Stored {len(video_ids)} recent video IDs for {channel.channel_name}"
        )
        return processed_videos

    def _extract_channel_id_from_url(self, channel_url: str) -> Optional[str]:
        """Extract channel ID or handle from URL"""
        if "@" in channel_url:
            # Handle format: @channelname
            return channel_url.split("@")[-1].split("/")[0]
        elif "/channel/" in channel_url:
            # Channel ID format: /channel/UC...
            return channel_url.split("/channel/")[-1].split("/")[0]
        elif "/c/" in channel_url:
            # Custom URL format: /c/channelname
            return channel_url.split("/c/")[-1].split("/")[0]
        else:
            # Try to use the whole URL as the identifier
            return channel_url.split("/")[-1] if "/" in channel_url else channel_url

    def process_video(self, metadata: VideoMetadata) -> Optional[ProcessedVideo]:
        """Process a single video"""
        logger.info(f"Processing video: {metadata.title}")

        try:
            # Check if video is already processed (has chunks in vector DB)
            if self.vector_db.video_chunks_exist(metadata.video_id):
                logger.info(f"Video {metadata.video_id} already processed, skipping")
                return ProcessedVideo(
                    video_id=metadata.video_id,
                    metadata=metadata,
                    summary="Already processed",
                    transcript_length=0,
                    processing_status="completed",
                    error_message="",
                )
            # Extract transcript
            transcript = self.transcript_extractor.extract_transcript(metadata.video_id)
            if not transcript:
                logger.warning(f"No transcript available for {metadata.video_id}")
                return ProcessedVideo(
                    video_id=metadata.video_id,
                    metadata=metadata,
                    summary="",
                    transcript_length=0,
                    processing_status="failed",
                    error_message="No transcript available",
                )

            # Generate summary
            summary = self.summarizer.chunk_and_summarize(transcript, metadata)
            if not summary:
                logger.error(f"Failed to generate summary for {metadata.video_id}")
                return ProcessedVideo(
                    video_id=metadata.video_id,
                    metadata=metadata,
                    summary="",
                    transcript_length=len(transcript),
                    processing_status="failed",
                    error_message="Summary generation failed",
                )

            # Store transcript chunks in vector database (new hierarchical approach)
            if hasattr(self.vector_db, "add_transcript_chunks"):
                # Get the raw transcript response for chunking
                supadata_response = self._get_supadata_transcript_response(
                    metadata.video_id
                )
                if supadata_response:
                    chunks_added = self.vector_db.add_transcript_chunks(
                        transcript_response=supadata_response,
                        channel_id=(
                            metadata.channel_url.split("/")[-1]
                            if "/" in metadata.channel_url
                            else metadata.channel_name
                        ),
                        channel_name=metadata.channel_name,
                        video_id=metadata.video_id,
                        video_title=metadata.title,
                        video_url=metadata.video_url,
                        publish_time=metadata.publish_time,
                        presenters=metadata.presenters,
                        category=getattr(metadata, "category", "general"),
                    )
                    logger.info(
                        f"Added {chunks_added} transcript chunks for video {metadata.video_id}"
                    )

            # Create processed video object
            processed_video = ProcessedVideo(
                video_id=metadata.video_id,
                metadata=metadata,
                summary=summary,
                transcript_length=len(transcript),
                processing_status="completed",
            )

            logger.info(f"Successfully processed video {metadata.video_id}")
            return processed_video

        except Exception as e:
            logger.error(f"Error processing video {metadata.video_id}: {e}")
            return ProcessedVideo(
                video_id=metadata.video_id,
                metadata=metadata,
                summary="",
                transcript_length=0,
                processing_status="error",
                error_message=str(e),
            )

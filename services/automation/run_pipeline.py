#!/usr/bin/env python3
"""
Production pipeline runner to process all enabled YouTube channels
Extracts recent videos and stores transcript chunks in Qdrant vector database
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Optional

# Add the automation service to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import CreatorListManager
from summarization_pipeline import SummarizationPipeline
from qdrant_vector_db import QdrantVectorDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/pipeline_run.log")],
)

logger = logging.getLogger(__name__)


def main(
    max_videos_per_channel: int = 5, specific_channels: Optional[List[str]] = None
):
    """
    Run the pipeline for all enabled channels

    Args:
        max_videos_per_channel: Maximum number of recent videos to process per channel
        specific_channels: Optional list of channel names to process (if None, processes all enabled)
    """
    try:
        logger.info("🚀 Starting YouTube automation pipeline...")

        # Initialize services
        creators_file = os.path.join(
            os.path.dirname(__file__), "youtube_creators_list.json"
        )
        creator_manager = CreatorListManager(creators_file)
        pipeline = SummarizationPipeline()
        vector_db = QdrantVectorDB()

        # Get enabled channels
        channels = creator_manager.get_enabled_channels()

        # Filter channels if specific ones requested
        if specific_channels:
            channels = [c for c in channels if c.channel_name in specific_channels]
            logger.info(
                f"Processing {len(channels)} specified channels: {', '.join(specific_channels)}"
            )
        else:
            logger.info(f"Processing {len(channels)} enabled channels")

        # Process each channel
        total_videos_processed = 0
        total_chunks_added = 0
        successful_channels = 0

        for i, channel in enumerate(channels, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(channels)}] Processing: {channel.channel_name}")
            logger.info(f"Channel ID: {channel.channel_id}")
            logger.info(f"Category: {channel.category}")
            logger.info(f"{'='*60}")

            try:
                # Process channel
                processed_videos = pipeline.process_channel(
                    channel, max_videos=max_videos_per_channel
                )

                if processed_videos:
                    successful_videos = [
                        v
                        for v in processed_videos
                        if v.processing_status == "completed"
                    ]
                    failed_videos = [
                        v
                        for v in processed_videos
                        if v.processing_status in ["failed", "error"]
                    ]

                    logger.info(
                        f"✅ {channel.channel_name}: {len(successful_videos)} successful, {len(failed_videos)} failed"
                    )
                    total_videos_processed += len(successful_videos)
                    successful_channels += 1

                    # Log video details
                    for video in successful_videos:
                        logger.info(
                            f"  ✓ {video.video_id}: {video.metadata.title[:50]}..."
                        )

                    if failed_videos:
                        for video in failed_videos:
                            logger.warning(
                                f"  ✗ {video.video_id}: {video.error_message}"
                            )

                else:
                    logger.warning(f"❌ No videos processed for {channel.channel_name}")

            except Exception as channel_error:
                logger.error(
                    f"❌ Error processing {channel.channel_name}: {channel_error}"
                )
                continue

        # Final statistics
        logger.info(f"\n{'='*60}")
        logger.info("📊 PIPELINE RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"✅ Channels processed: {successful_channels}/{len(channels)}")
        logger.info(f"✅ Videos processed: {total_videos_processed}")

        # Get database stats
        try:
            db_stats = vector_db.get_stats()
            total_points = db_stats.get("total_points", 0)
            logger.info(f"✅ Total transcript chunks in Qdrant: {total_points}")

            # Show channel distribution if available
            channel_dist = db_stats.get("channel_distribution", {})
            if channel_dist:
                logger.info("📈 Channel distribution:")
                for channel_name, count in sorted(
                    channel_dist.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    logger.info(f"  • {channel_name}: {count} chunks")

        except Exception as stats_error:
            logger.warning(f"Could not get database stats: {stats_error}")

        logger.info(f"🎯 Pipeline completed at {datetime.now().isoformat()}")

        return {
            "success": True,
            "channels_processed": successful_channels,
            "videos_processed": total_videos_processed,
            "total_channels": len(channels),
        }

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()

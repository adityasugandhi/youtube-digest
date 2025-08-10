"""
Scheduler service for automated YouTube summarization pipeline
"""

import os
import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import signal
import sys

from models import CreatorListManager
from summarization_pipeline import SummarizationPipeline
from vector_db import ChromaVectorDB

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Automated YouTube summarization scheduler"""

    def __init__(self):
        self.creators_file = os.path.join(
            os.path.dirname(__file__), "youtube_creators_list.json"
        )
        self.creator_manager = CreatorListManager(self.creators_file)
        self.pipeline = SummarizationPipeline()
        self.vector_db = ChromaVectorDB()
        self.running = False
        self.stats = {
            "last_run": None,
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "videos_processed": 0,
            "videos_added_to_db": 0,
        }

    def setup_logging(self):
        """Set up logging configuration"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("automation.log"),
            ],
        )

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run_pipeline(self) -> Dict[str, Any]:
        """Run the complete pipeline for all channels"""
        start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info("🚀 Starting automated YouTube summarization pipeline")
        logger.info("=" * 60)

        run_stats = {
            "start_time": start_time.isoformat(),
            "channels_processed": 0,
            "videos_found": 0,
            "videos_processed": 0,
            "videos_added_to_db": 0,
            "errors": [],
        }

        try:
            # Get enabled channels
            channels = self.creator_manager.get_enabled_channels()
            logger.info(f"Processing {len(channels)} enabled channels")

            for channel in channels:
                try:
                    logger.info(f"📺 Processing channel: {channel.channel_name}")

                    # Process channel
                    processed_videos = self.pipeline.process_channel(
                        channel, max_videos=5
                    )
                    run_stats["videos_found"] += len(processed_videos)

                    # Filter successful videos
                    successful_videos = [
                        v
                        for v in processed_videos
                        if v.processing_status == "completed"
                    ]
                    run_stats["videos_processed"] += len(successful_videos)

                    # Add to vector database
                    if successful_videos:
                        added_count = self.vector_db.add_documents_batch(
                            successful_videos
                        )
                        run_stats["videos_added_to_db"] += added_count
                        logger.info(
                            f"✅ Added {added_count} new summaries to vector database"
                        )

                    # Update last processed timestamp
                    self.creator_manager.update_last_processed(
                        channel.channel_name, start_time.isoformat()
                    )

                    run_stats["channels_processed"] += 1
                    logger.info(f"✅ Completed channel: {channel.channel_name}")

                    # Rate limiting between channels
                    time.sleep(5)

                except Exception as e:
                    error_msg = (
                        f"Error processing channel {channel.channel_name}: {str(e)}"
                    )
                    logger.error(error_msg)
                    run_stats["errors"].append(error_msg)
                    continue

            # Update global stats
            self.stats["total_runs"] += 1
            self.stats["last_run"] = start_time.isoformat()

            if run_stats["errors"]:
                self.stats["failed_runs"] += 1
                run_stats["status"] = "completed_with_errors"
            else:
                self.stats["successful_runs"] += 1
                run_stats["status"] = "success"

            self.stats["videos_processed"] += run_stats["videos_processed"]
            self.stats["videos_added_to_db"] += run_stats["videos_added_to_db"]

            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            run_stats["duration_seconds"] = duration
            run_stats["end_time"] = end_time.isoformat()

            logger.info("=" * 60)
            logger.info("📊 PIPELINE SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✅ Channels processed: {run_stats['channels_processed']}")
            logger.info(f"📹 Videos found: {run_stats['videos_found']}")
            logger.info(f"🤖 Videos processed: {run_stats['videos_processed']}")
            logger.info(f"💾 Videos added to DB: {run_stats['videos_added_to_db']}")
            logger.info(f"⚠️  Errors: {len(run_stats['errors'])}")
            logger.info(f"⏱️  Duration: {duration:.1f} seconds")
            logger.info("=" * 60)

            if run_stats["errors"]:
                logger.warning("Errors encountered:")
                for error in run_stats["errors"]:
                    logger.warning(f"  - {error}")

            return run_stats

        except Exception as e:
            self.stats["failed_runs"] += 1
            self.stats["total_runs"] += 1
            error_msg = f"Pipeline failed: {str(e)}"
            logger.error(error_msg)
            run_stats["status"] = "failed"
            run_stats["error"] = error_msg
            return run_stats

    def run_test_pipeline(self, channel_name: str = None) -> Dict[str, Any]:
        """Run pipeline for testing (single channel or all)"""
        logger.info(f"🧪 Running test pipeline for: {channel_name or 'all channels'}")

        if channel_name:
            # Test single channel
            channels = self.creator_manager.get_enabled_channels()
            test_channel = next(
                (c for c in channels if c.channel_name == channel_name), None
            )

            if not test_channel:
                logger.error(f"Channel {channel_name} not found")
                return {"status": "error", "message": "Channel not found"}

            processed_videos = self.pipeline.process_channel(test_channel, max_videos=2)

            result = {
                "status": "success",
                "channel": channel_name,
                "videos_processed": len(processed_videos),
                "results": [v.to_dict() for v in processed_videos],
            }

            return result
        else:
            # Run full pipeline once
            return self.run_pipeline()

    def start_scheduler(self):
        """Start the hourly scheduler"""
        logger.info("🚀 Starting YouTube summarization scheduler")

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Schedule the pipeline to run every hour
        schedule.every().hour.at(":00").do(self.run_pipeline)

        # Optional: Run immediately on startup
        if os.getenv("RUN_ON_STARTUP", "false").lower() == "true":
            logger.info("Running pipeline on startup...")
            self.run_pipeline()

        self.running = True
        logger.info("⏰ Scheduler started - pipeline will run every hour")
        logger.info("📊 Vector database stats:")
        db_stats = self.vector_db.get_stats()
        for key, value in db_stats.items():
            logger.info(f"   {key}: {value}")

        # Main scheduler loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

        logger.info("🛑 Scheduler stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        db_stats = self.vector_db.get_stats()

        return {
            "scheduler_stats": self.stats,
            "database_stats": db_stats,
            "next_run": schedule.next_run().isoformat() if schedule.jobs else None,
            "status": "running" if self.running else "stopped",
        }


# Production scheduler - no CLI interface
# Use start_automation.py for proper service management


if __name__ == "__main__":
    # Direct scheduler execution (not recommended for production)
    # Use start_automation.py instead
    scheduler = PipelineScheduler()
    scheduler.setup_logging()
    scheduler.start_scheduler()

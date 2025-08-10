#!/usr/bin/env python3
"""
Startup script for YouTube automation pipeline with pre-startup validation
"""
import os
import sys
import logging
import signal
import time
from datetime import datetime
import threading
import argparse
import asyncio

from scheduler import PipelineScheduler
from api import app
from pre_startup_tests import PreStartupValidator
from health_monitor import HealthMonitor
import uvicorn


class AutomationService:
    """Combined automation service (API + Scheduler)"""

    def __init__(self, mode="combined", skip_validation=False):
        self.mode = mode
        self.skip_validation = skip_validation
        self.scheduler = PipelineScheduler()
        self.api_server = None
        self.scheduler_thread = None
        self.running = False
        self.health_monitor = HealthMonitor()

        # Set up logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_logging(self):
        """Set up production logging configuration"""
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        handlers = [logging.StreamHandler(sys.stdout)]

        # Add file handler if log directory exists
        log_dir = os.getenv("LOG_DIR", "./logs")
        if os.path.exists(log_dir) or os.makedirs(log_dir, exist_ok=True):
            handlers.append(logging.FileHandler(f"{log_dir}/automation.log", mode="a"))

        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=handlers,
        )

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

        if self.scheduler:
            self.scheduler.running = False

        if self.api_server:
            self.api_server.should_exit = True

    def start_api_server(self):
        """Start the API server"""
        try:
            port = int(os.getenv("AUTOMATION_API_PORT", "8003"))
            self.logger.info(f"Starting API server on port {port}")

            config = uvicorn.Config(
                app, host="0.0.0.0", port=port, log_level="info", access_log=True
            )

            self.api_server = uvicorn.Server(config)
            self.api_server.run()

        except Exception as e:
            self.logger.error(f"API server error: {e}")

    def start_scheduler_only(self):
        """Start only the scheduler"""
        try:
            self.logger.info("Starting scheduler service")
            self.scheduler.start_scheduler()
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")

    def start_api_only(self):
        """Start only the API server"""
        try:
            self.start_api_server()
        except Exception as e:
            self.logger.error(f"API only mode error: {e}")

    def start_combined(self):
        """Start both API server and scheduler"""
        self.running = True
        self.logger.info("=" * 60)
        self.logger.info("🚀 Starting YouTube Automation Pipeline")
        self.logger.info("=" * 60)
        self.logger.info("Mode: Combined (API + Scheduler)")

        try:
            # Start scheduler in a separate thread
            self.scheduler_thread = threading.Thread(
                target=self.scheduler.start_scheduler, daemon=True
            )
            self.scheduler_thread.start()
            self.logger.info("✅ Scheduler thread started")

            # Wait a moment for scheduler to initialize
            time.sleep(2)

            # Start API server in main thread
            self.logger.info("🌐 Starting API server...")
            self.start_api_server()

        except Exception as e:
            self.logger.error(f"Combined mode error: {e}")
        finally:
            self.logger.info("🛑 Automation service stopped")

    def run_pre_startup_validation(self):
        """Run comprehensive pre-startup validation"""
        if self.skip_validation:
            self.logger.warning("⚠️  Pre-startup validation SKIPPED")
            return True

        self.logger.info("🔍 Running pre-startup validation...")

        validator = PreStartupValidator()
        success = validator.run_all_tests()

        if not success:
            self.logger.critical("💥 Pre-startup validation FAILED!")
            self.logger.critical(
                "Service will NOT start. Fix the issues above and try again."
            )
            return False

        self.logger.info("✅ Pre-startup validation PASSED - Service ready to start!")
        return True

    def start(self):
        """Start the service based on mode with pre-startup validation"""
        self.logger.info(f"🚀 Starting YouTube Automation Service (mode: {self.mode})")

        # Run pre-startup validation
        if not self.run_pre_startup_validation():
            sys.exit(1)

        # Print startup information
        self.print_startup_info()

        # Start appropriate mode
        if self.mode == "api":
            self.start_api_only()
        elif self.mode == "scheduler":
            self.start_scheduler_only()
        else:  # combined
            self.start_combined()

    def print_startup_info(self):
        """Print startup information"""
        try:
            from vector_db import ChromaVectorDB

            vector_db = ChromaVectorDB()
            db_stats = vector_db.get_stats()

            from models import CreatorListManager

            creators_file = os.path.join(
                os.path.dirname(__file__), "youtube_creators_list.json"
            )
            creator_manager = CreatorListManager(creators_file)
            channels = creator_manager.get_enabled_channels()

            self.logger.info("📊 Current Status:")
            self.logger.info(f"   📺 Enabled channels: {len(channels)}")
            self.logger.info(
                f"   💾 Vector database documents: {db_stats.get('total_documents', 0)}"
            )
            self.logger.info(
                f"   🔑 YouTube API Key: {'✅ Set' if os.getenv('YOUTUBE_API_KEY') else '❌ Missing'}"
            )
            self.logger.info(
                f"   🤖 Gemini API Key: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Missing'}"
            )
            self.logger.info(
                f"   📂 ChromaDB Path: {os.getenv('CHROMA_DB_PATH', './data/chroma_db')}"
            )
            self.logger.info("")

            self.logger.info("🎯 Enabled Channels:")
            for channel in channels:
                self.logger.info(
                    f"   • {channel.channel_name} ({', '.join(channel.presenters)})"
                )

        except Exception as e:
            self.logger.warning(f"Could not load startup info: {e}")


def main():
    """Main entry point for production automation service"""
    parser = argparse.ArgumentParser(description="YouTube Automation Pipeline")
    parser.add_argument(
        "--mode",
        choices=["combined", "api", "scheduler"],
        default="combined",
        help="Service mode: combined (API + Scheduler), api (API only), or scheduler (Scheduler only)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip pre-startup validation tests (NOT recommended for production)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation tests only and exit (don't start service)",
    )

    args = parser.parse_args()

    if args.validate_only:
        # Run validation tests only
        print("🔍 Running validation tests only...")
        validator = PreStartupValidator()
        success = validator.run_all_tests()
        sys.exit(0 if success else 1)

    # Start the service
    service = AutomationService(mode=args.mode, skip_validation=args.skip_validation)
    service.start()


if __name__ == "__main__":
    main()

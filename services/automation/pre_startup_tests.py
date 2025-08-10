#!/usr/bin/env python3
"""
Pre-startup tests to verify all components before service launch
Validates APIs, database, environment, and configurations
"""
import os
import sys
import json
import logging
import time
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PreStartupValidator:
    """Comprehensive pre-startup validation suite"""

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.failed_tests = 0
        self.passed_tests = 0

    def add_result(
        self,
        test_name: str,
        success: bool,
        message: str,
        details: Optional[Dict] = None,
    ):
        """Add test result to tracking"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
        }
        self.test_results.append(result)

        if success:
            self.passed_tests += 1
            logger.info(f"✅ {test_name}: {message}")
        else:
            self.failed_tests += 1
            logger.error(f"❌ {test_name}: {message}")
            if details:
                logger.error(f"   Details: {details}")

    def test_environment_variables(self) -> bool:
        """Test all required environment variables"""
        logger.info("🔍 Testing environment variables...")

        required_vars = {
            "YOUTUBE_API_KEY": "YouTube Data API key",
            "SUPABASE_YOUTUBE_API": "Supabase transcript API key",
            "GEMINI_API_KEY": "Google Gemini API key",
        }

        optional_vars = {
            "AUTOMATION_API_PORT": "API server port (default: 8003)",
            "LOG_LEVEL": "Logging level (default: INFO)",
            "CHROMA_DB_HOST": "ChromaDB host for internal Docker network (default: chromadb)",
            "CHROMA_DB_PORT": "ChromaDB port for internal Docker network (default: 8000)",
            "CHROMA_HOST": "ChromaDB host for external connection (default: localhost)",
            "CHROMA_PORT": "ChromaDB port for external connection (default: 4545)",
            "CHROMA_DB_PATH": "ChromaDB local path fallback (default: ./data/chroma_db)",
        }

        all_good = True
        missing_required = []
        present_vars = {}

        # Check required variables
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                # Don't log full API keys, just indicate presence
                masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
                present_vars[var] = masked_value
            else:
                missing_required.append(f"{var} ({description})")
                all_good = False

        # Check optional variables
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                present_vars[var] = value

        if all_good:
            self.add_result(
                "Environment Variables",
                True,
                f"All {len(required_vars)} required environment variables present",
                {"present_vars": present_vars},
            )
        else:
            self.add_result(
                "Environment Variables",
                False,
                f"Missing required variables: {', '.join(missing_required)}",
                {"missing": missing_required, "present_vars": present_vars},
            )

        return all_good

    def test_youtube_api_connectivity(self) -> bool:
        """Test YouTube Data API connectivity and quota"""
        logger.info("📺 Testing YouTube API connectivity...")

        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError

            api_key = os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                self.add_result(
                    "YouTube API Connectivity",
                    False,
                    "No YouTube API key found in environment",
                )
                return False

            youtube = build("youtube", "v3", developerKey=api_key)

            # Test with a simple search request
            test_response = (
                youtube.search()
                .list(part="snippet", q="test", type="channel", maxResults=1)
                .execute()
            )

            quota_used = test_response.get("pageInfo", {}).get("totalResults", 0)

            self.add_result(
                "YouTube API Connectivity",
                True,
                "YouTube API connection successful",
                {
                    "quota_cost": "~100 units",
                    "response_items": len(test_response.get("items", [])),
                    "api_version": "v3",
                },
            )
            return True

        except HttpError as e:
            error_details = {"status_code": e.resp.status, "reason": str(e)}
            if e.resp.status == 403:
                message = "YouTube API quota exceeded or invalid key"
            elif e.resp.status == 400:
                message = "YouTube API request malformed"
            else:
                message = f"YouTube API HTTP error: {e.resp.status}"

            self.add_result("YouTube API Connectivity", False, message, error_details)
            return False

        except Exception as e:
            self.add_result(
                "YouTube API Connectivity",
                False,
                f"YouTube API connection failed: {str(e)}",
            )
            return False

    def test_supabase_api_connectivity(self) -> bool:
        """Test Supabase API connectivity"""
        logger.info("🔗 Testing Supabase API connectivity...")

        try:
            import requests

            api_key = os.getenv("SUPABASE_YOUTUBE_API")
            if not api_key:
                self.add_result(
                    "Supabase API Connectivity",
                    False,
                    "No Supabase API key found in environment",
                )
                return False

            # Test with a simple video (Rick Roll - always available)
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

            response = requests.get(
                f"https://api.supadata.ai/v1/transcript?url={test_url}",
                headers={"x-api-key": api_key},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                transcript_length = len(data.get("content", []))

                self.add_result(
                    "Supabase API Connectivity",
                    True,
                    "Supabase API connection successful",
                    {
                        "response_code": response.status_code,
                        "transcript_segments": transcript_length,
                        "test_video": "Rick Astley - Never Gonna Give You Up",
                    },
                )
                return True
            else:
                self.add_result(
                    "Supabase API Connectivity",
                    False,
                    f"Supabase API returned status {response.status_code}",
                    {"response_text": response.text[:200]},
                )
                return False

        except requests.exceptions.Timeout:
            self.add_result(
                "Supabase API Connectivity",
                False,
                "Supabase API request timed out (10s)",
            )
            return False

        except Exception as e:
            self.add_result(
                "Supabase API Connectivity",
                False,
                f"Supabase API test failed: {str(e)}",
            )
            return False

    def test_gemini_api_connectivity(self) -> bool:
        """Test Gemini API connectivity"""
        logger.info("🤖 Testing Gemini API connectivity...")

        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                self.add_result(
                    "Gemini API Connectivity",
                    False,
                    "No Gemini API key found in environment",
                )
                return False

            genai.configure(api_key=api_key)

            # Test embedding generation (cheaper than text generation)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content="test connectivity",
                task_type="retrieval_document",
            )

            embedding_dim = len(result["embedding"])

            # Test text generation with minimal token usage
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            response = model.generate_content("Say 'OK' if you can hear me.")
            generated_text = response.text.strip()

            self.add_result(
                "Gemini API Connectivity",
                True,
                "Gemini API connection successful",
                {
                    "embedding_dimensions": embedding_dim,
                    "text_generation_response": generated_text[:50],
                    "models_tested": ["text-embedding-004", "gemini-2.0-flash-exp"],
                },
            )
            return True

        except Exception as e:
            self.add_result(
                "Gemini API Connectivity", False, f"Gemini API test failed: {str(e)}"
            )
            return False

    def test_database_connectivity(self) -> bool:
        """Test ChromaDB database connectivity and initialization (Docker or local)"""
        logger.info("🗄️ Testing database connectivity...")

        try:
            import chromadb
            from chromadb.config import Settings

            # Try Docker container first (internal network for automation service)
            chroma_host = os.getenv(
                "CHROMA_DB_HOST", os.getenv("CHROMA_HOST", "localhost")
            )
            chroma_port = int(
                os.getenv("CHROMA_DB_PORT", os.getenv("CHROMA_PORT", 4545))
            )
            connection_type = None

            try:
                client = chromadb.HttpClient(
                    host=chroma_host,
                    port=chroma_port,
                    settings=Settings(anonymized_telemetry=False),
                )
                client.heartbeat()  # Test connection
                connection_type = f"Docker container ({chroma_host}:{chroma_port})"

            except Exception as e:
                logger.info(f"Docker ChromaDB not available: {e}")
                # Fallback to local persistent
                db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
                client = chromadb.PersistentClient(
                    path=db_path,
                    settings=Settings(anonymized_telemetry=False, allow_reset=False),
                )
                connection_type = f"Local persistent ({db_path})"

            # Try to get/create the collection
            collection = client.get_or_create_collection(
                name="youtube_summaries",
                metadata={"description": "YouTube video summaries and embeddings"},
            )

            doc_count = collection.count()

            # Test basic operations
            test_id = f"test_{int(time.time())}"
            test_embedding = [0.1] * 768  # Mock embedding

            # Add test document
            collection.add(
                ids=[test_id],
                embeddings=[test_embedding],
                documents=["test document"],
                metadatas=[{"type": "startup_test"}],
            )

            # Query test document
            query_results = collection.get(ids=[test_id])

            # Clean up test document
            collection.delete(ids=[test_id])

            self.add_result(
                "Database Connectivity",
                True,
                "ChromaDB connection and operations successful",
                {
                    "connection_type": connection_type,
                    "existing_documents": doc_count,
                    "collection_name": "youtube_summaries",
                    "test_operations": ["add", "get", "delete"],
                },
            )
            return True

        except Exception as e:
            self.add_result(
                "Database Connectivity", False, f"Database test failed: {str(e)}"
            )
            return False

    def test_channel_configuration(self) -> bool:
        """Test YouTube creators configuration file"""
        logger.info("📋 Testing channel configuration...")

        try:
            config_path = os.path.join(
                os.path.dirname(__file__), "youtube_creators_list.json"
            )

            if not os.path.exists(config_path):
                self.add_result(
                    "Channel Configuration",
                    False,
                    f"Configuration file not found: {config_path}",
                )
                return False

            with open(config_path, "r") as f:
                config_data = json.load(f)

            if not isinstance(config_data, list):
                self.add_result(
                    "Channel Configuration",
                    False,
                    "Configuration should be a list of channel objects",
                )
                return False

            required_fields = [
                "channel_name",
                "channel_url",
                "presenters",
                "channel_id",
                "enabled",
                "category",
            ]
            enabled_channels = []
            missing_channel_ids = []

            for i, channel in enumerate(config_data):
                # Check required fields
                for field in required_fields:
                    if field not in channel:
                        self.add_result(
                            "Channel Configuration",
                            False,
                            f"Channel {i} missing required field: {field}",
                        )
                        return False

                if channel["enabled"]:
                    enabled_channels.append(channel["channel_name"])
                    if not channel["channel_id"]:
                        missing_channel_ids.append(channel["channel_name"])

            if missing_channel_ids:
                self.add_result(
                    "Channel Configuration",
                    False,
                    f"Enabled channels missing channel_id: {', '.join(missing_channel_ids)}",
                )
                return False

            self.add_result(
                "Channel Configuration",
                True,
                f"Configuration valid with {len(enabled_channels)} enabled channels",
                {
                    "total_channels": len(config_data),
                    "enabled_channels": len(enabled_channels),
                    "enabled_channel_names": enabled_channels,
                    "config_file": config_path,
                },
            )
            return True

        except json.JSONDecodeError as e:
            self.add_result(
                "Channel Configuration",
                False,
                f"Invalid JSON in configuration file: {str(e)}",
            )
            return False

        except Exception as e:
            self.add_result(
                "Channel Configuration", False, f"Configuration test failed: {str(e)}"
            )
            return False

    def test_dependencies(self) -> bool:
        """Test all required dependencies are installed"""
        logger.info("📦 Testing dependencies...")

        required_modules = {
            "fastapi": "Web framework",
            "uvicorn": "ASGI server",
            "chromadb": "Vector database",
            "google.generativeai": "Gemini AI",
            "googleapiclient": "YouTube API",
            "youtube_transcript_api": "Transcript extraction",
            "requests": "HTTP client",
            "schedule": "Task scheduler",
            "pydantic": "Data validation",
        }

        missing_modules = []
        installed_versions = {}

        for module, description in required_modules.items():
            try:
                imported_module = __import__(module)
                version = getattr(imported_module, "__version__", "unknown")
                installed_versions[module] = version
            except ImportError:
                missing_modules.append(f"{module} ({description})")

        if missing_modules:
            self.add_result(
                "Dependencies",
                False,
                f"Missing required modules: {', '.join(missing_modules)}",
            )
            return False
        else:
            self.add_result(
                "Dependencies",
                True,
                f"All {len(required_modules)} required modules installed",
                {"installed_versions": installed_versions},
            )
            return True

    def test_file_permissions(self) -> bool:
        """Test file system permissions for logs and database"""
        logger.info("📁 Testing file permissions...")

        try:
            # Test log directory
            log_dir = os.getenv("LOG_DIR", "./logs")
            os.makedirs(log_dir, exist_ok=True)

            # Test database directory
            db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
            db_dir = os.path.dirname(db_path)
            os.makedirs(db_dir, exist_ok=True)

            # Test write permissions
            test_log_file = os.path.join(log_dir, "permission_test.log")
            with open(test_log_file, "w") as f:
                f.write("permission test")
            os.remove(test_log_file)

            self.add_result(
                "File Permissions",
                True,
                "All required directories writable",
                {
                    "log_directory": log_dir,
                    "database_directory": db_dir,
                    "permissions": "read/write",
                },
            )
            return True

        except Exception as e:
            self.add_result(
                "File Permissions", False, f"File permission test failed: {str(e)}"
            )
            return False

    def run_all_tests(self) -> bool:
        """Run all pre-startup tests"""
        logger.info("🚀 Starting pre-startup validation tests...")
        start_time = time.time()

        # Run all tests
        tests = [
            self.test_dependencies,
            self.test_environment_variables,
            self.test_file_permissions,
            self.test_database_connectivity,
            self.test_channel_configuration,
            self.test_youtube_api_connectivity,
            self.test_supabase_api_connectivity,
            self.test_gemini_api_connectivity,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                self.add_result(
                    test.__name__.replace("test_", "").replace("_", " ").title(),
                    False,
                    f"Test crashed: {str(e)}",
                )

        duration = time.time() - start_time

        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info(f"PRE-STARTUP VALIDATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Tests: {len(self.test_results)}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {self.failed_tests}")
        logger.info(f"Duration: {duration:.2f}s")

        if self.failed_tests == 0:
            logger.info("🎉 ALL TESTS PASSED - Service ready to start!")
            return True
        else:
            logger.error(f"❌ {self.failed_tests} TESTS FAILED - Service NOT ready")
            logger.error("Fix the above issues before starting the service.")
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Generate detailed test report"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_tests": len(self.test_results),
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "success_rate": (
                    f"{(self.passed_tests/len(self.test_results)*100):.1f}%"
                    if self.test_results
                    else "0%"
                ),
            },
            "tests": self.test_results,
        }


def main():
    """Main test runner"""
    validator = PreStartupValidator()

    success = validator.run_all_tests()

    # Save detailed report
    report = validator.generate_report()
    report_file = f"startup_validation_report_{int(time.time())}.json"

    try:
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"📄 Detailed report saved to: {report_file}")
    except Exception as e:
        logger.warning(f"Could not save report: {e}")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

"""
Runtime health monitoring and diagnostics
"""

import os
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""

    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthMonitor:
    """System health monitoring"""

    def __init__(self):
        self.last_checks: Dict[str, HealthCheck] = {}
        self.check_history: List[HealthCheck] = []
        self.max_history = 100

    async def check_supadata_api_health(self) -> HealthCheck:
        """Check Supadata API health"""
        start_time = time.time()

        try:
            from supadata import Supadata, SupadataError

            api_key = os.getenv("SUPADATA_API_KEY")
            if not api_key:
                return HealthCheck(
                    name="supadata_api",
                    status=HealthStatus.CRITICAL,
                    message="Supadata API key not configured",
                    timestamp=datetime.utcnow(),
                )

            supadata = Supadata(api_key=api_key)

            # Test API with a known video ID
            response = supadata.youtube.video(id="dQw4w9WgXcQ")

            response_time = (time.time() - start_time) * 1000

            if response and response.id:
                status = HealthStatus.HEALTHY
                message = "Supadata API responding normally"
                details = {
                    "test_video_id": response.id,
                    "video_title": (
                        response.title[:50] + "..."
                        if len(response.title) > 50
                        else response.title
                    ),
                }
            else:
                status = HealthStatus.WARNING
                message = "Supadata API responding but no data"
                details = {}

            return HealthCheck(
                name="supadata_api",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details=details,
            )

        except SupadataError as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="supadata_api",
                status=HealthStatus.CRITICAL,
                message=f"Supadata API error: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details={"error": str(e)},
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="supadata_api",
                status=HealthStatus.CRITICAL,
                message=f"Supadata API connection failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details={"error": str(e)},
            )

    async def check_supabase_api_health(self) -> HealthCheck:
        """Check Supabase API health"""
        start_time = time.time()

        try:
            import requests

            api_key = os.getenv("SUPABASE_YOUTUBE_API")
            if not api_key:
                return HealthCheck(
                    name="supabase_api",
                    status=HealthStatus.CRITICAL,
                    message="Supabase API key not configured",
                    timestamp=datetime.utcnow(),
                )

            # Simple health check with HEAD request to avoid quota
            response = requests.head(
                "https://api.supadata.ai/v1/transcript",
                headers={"x-api-key": api_key},
                timeout=5,
            )

            response_time = (time.time() - start_time) * 1000

            if response.status_code in [
                200,
                400,
            ]:  # 400 is expected for HEAD without URL
                status = HealthStatus.HEALTHY
                message = "Supabase API responding normally"
            elif response.status_code in [500, 502, 503, 504]:
                status = HealthStatus.WARNING
                message = f"Supabase API server issues: {response.status_code}"
            else:
                status = HealthStatus.CRITICAL
                message = f"Supabase API error: {response.status_code}"

            return HealthCheck(
                name="supabase_api",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details={"status_code": response.status_code},
            )

        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="supabase_api",
                status=HealthStatus.WARNING,
                message="Supabase API timeout (>5s)",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="supabase_api",
                status=HealthStatus.CRITICAL,
                message=f"Supabase API connection failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
            )

    async def check_gemini_api_health(self) -> HealthCheck:
        """Check Gemini API health"""
        start_time = time.time()

        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return HealthCheck(
                    name="gemini_api",
                    status=HealthStatus.CRITICAL,
                    message="Gemini API key not configured",
                    timestamp=datetime.utcnow(),
                )

            genai.configure(api_key=api_key)

            # Lightweight embedding test (cheaper than text generation)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content="health check",
                task_type="retrieval_document",
            )

            response_time = (time.time() - start_time) * 1000

            if result and "embedding" in result:
                status = HealthStatus.HEALTHY
                message = "Gemini API responding normally"
                details = {
                    "embedding_dimensions": len(result["embedding"]),
                    "model": "text-embedding-004",
                }
            else:
                status = HealthStatus.WARNING
                message = "Gemini API responding but unexpected format"
                details = {"response_keys": list(result.keys()) if result else []}

            return HealthCheck(
                name="gemini_api",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details=details,
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # Parse common Gemini API errors
            error_message = str(e).lower()
            if "quota" in error_message or "limit" in error_message:
                status = HealthStatus.CRITICAL
                message = "Gemini API quota exceeded"
            elif "unauthorized" in error_message or "permission" in error_message:
                status = HealthStatus.CRITICAL
                message = "Gemini API authentication failed"
            else:
                status = HealthStatus.WARNING
                message = f"Gemini API error: {str(e)}"

            return HealthCheck(
                name="gemini_api",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
            )

    async def check_database_health(self) -> HealthCheck:
        """Check ChromaDB health (Docker container or local)"""
        start_time = time.time()

        try:
            import chromadb
            from chromadb.config import Settings

            # Try Docker container first
            chroma_host = os.getenv("CHROMA_HOST", "localhost")  # External connection
            chroma_port = int(os.getenv("CHROMA_PORT", 4545))  # External port

            try:
                client = chromadb.HttpClient(
                    host=chroma_host,
                    port=chroma_port,
                    settings=Settings(anonymized_telemetry=False),
                )
                client.heartbeat()  # Test connection
                connection_type = f"Docker container ({chroma_host}:{chroma_port})"

            except Exception:
                # Fallback to local persistent
                db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
                client = chromadb.PersistentClient(
                    path=db_path,
                    settings=Settings(anonymized_telemetry=False, allow_reset=False),
                )
                connection_type = f"Local persistent ({db_path})"

            collection = client.get_or_create_collection(
                name="youtube_summaries",
                metadata={"description": "YouTube video summaries and embeddings"},
            )

            doc_count = collection.count()
            response_time = (time.time() - start_time) * 1000

            # Check if database is accessible and responsive
            if response_time > 5000:  # 5 seconds
                status = HealthStatus.WARNING
                message = f"Database responding slowly ({response_time:.0f}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = "Database responding normally"

            return HealthCheck(
                name="database",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details={
                    "document_count": doc_count,
                    "connection_type": connection_type,
                    "collection": "youtube_summaries",
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
            )

    async def check_system_resources(self) -> HealthCheck:
        """Check system resources (memory, disk)"""
        start_time = time.time()

        try:
            import psutil

            # Memory check
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk check for database directory
            db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
            disk = psutil.disk_usage(os.path.dirname(os.path.abspath(db_path)))
            disk_percent = (disk.used / disk.total) * 100

            response_time = (time.time() - start_time) * 1000

            # Determine status based on resource usage
            if memory_percent > 90 or disk_percent > 95:
                status = HealthStatus.CRITICAL
                message = "System resources critically low"
            elif memory_percent > 80 or disk_percent > 90:
                status = HealthStatus.WARNING
                message = "System resources running low"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"

            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details={
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "memory_available_gb": round(memory.available / (1024**3), 1),
                    "disk_free_gb": round(disk.free / (1024**3), 1),
                },
            )

        except ImportError:
            # psutil not available, skip resource monitoring
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message="Resource monitoring unavailable (psutil not installed)",
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.WARNING,
                message=f"Resource check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
            )

    async def run_all_health_checks(self) -> Dict[str, Any]:
        """Run all health checks concurrently"""
        logger.info("🏥 Running health checks...")

        # Run checks concurrently
        checks = await asyncio.gather(
            self.check_database_health(),
            self.check_supadata_api_health(),
            self.check_supabase_api_health(),
            self.check_gemini_api_health(),
            self.check_system_resources(),
            return_exceptions=True,
        )

        # Process results
        results = {}
        overall_status = HealthStatus.HEALTHY

        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check failed with exception: {check}")
                continue

            # Store result
            results[check.name] = {
                "status": check.status.value,
                "message": check.message,
                "timestamp": check.timestamp.isoformat(),
                "response_time_ms": check.response_time_ms,
                "details": check.details,
            }

            # Update last check
            self.last_checks[check.name] = check

            # Add to history
            self.check_history.append(check)
            if len(self.check_history) > self.max_history:
                self.check_history = self.check_history[-self.max_history :]

            # Update overall status
            if check.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif (
                check.status == HealthStatus.WARNING
                and overall_status != HealthStatus.CRITICAL
            ):
                overall_status = HealthStatus.WARNING

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results,
            "summary": {
                "total_checks": len(results),
                "healthy": sum(1 for r in results.values() if r["status"] == "healthy"),
                "warning": sum(1 for r in results.values() if r["status"] == "warning"),
                "critical": sum(
                    1 for r in results.values() if r["status"] == "critical"
                ),
            },
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of last health check results"""
        if not self.last_checks:
            return {
                "overall_status": "unknown",
                "message": "No health checks performed yet",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Determine overall status from last checks
        statuses = [check.status for check in self.last_checks.values()]

        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "last_check": max(
                check.timestamp for check in self.last_checks.values()
            ).isoformat(),
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                }
                for name, check in self.last_checks.items()
            },
        }

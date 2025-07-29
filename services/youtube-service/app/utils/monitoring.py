from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import time
import functools
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Create custom registry for this service
REGISTRY = CollectorRegistry()

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    registry=REGISTRY
)

TRANSCRIPT_PROCESSING_TIME = Histogram(
    'transcript_processing_seconds',
    'Time to process transcript',
    registry=REGISTRY
)

YOUTUBE_API_CALLS = Counter(
    'youtube_api_calls_total',
    'Total YouTube API calls',
    ['endpoint', 'status'],
    registry=REGISTRY
)

YOUTUBE_QUOTA_USAGE = Gauge(
    'youtube_quota_used',
    'YouTube API quota used',
    registry=REGISTRY
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Active database connections',
    registry=REGISTRY
)


def monitor_endpoint(func):
    """Decorator to monitor endpoint performance"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(
                method='GET', 
                endpoint=func.__name__, 
                status='success'
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                method='GET', 
                endpoint=func.__name__, 
                status='error'
            ).inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    
    return wrapper


def monitor_youtube_api(func):
    """Decorator to monitor YouTube API calls"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            YOUTUBE_API_CALLS.labels(
                endpoint=func.__name__,
                status='success'
            ).inc()
            return result
        except Exception as e:
            YOUTUBE_API_CALLS.labels(
                endpoint=func.__name__,
                status='error'
            ).inc()
            raise
        finally:
            # Update quota usage if this is a YouTubeClient instance
            if hasattr(args[0], 'quota_used'):
                YOUTUBE_QUOTA_USAGE.set(args[0].quota_used)
    
    return wrapper


async def setup_monitoring():
    """Setup monitoring for the service"""
    logger.info("Setting up monitoring...")
    
    # Initialize metrics
    REQUEST_COUNT.labels(method='GET', endpoint='init', status='success').inc(0)
    REQUEST_DURATION.observe(0)
    TRANSCRIPT_PROCESSING_TIME.observe(0)
    YOUTUBE_API_CALLS.labels(endpoint='init', status='success').inc(0)
    YOUTUBE_QUOTA_USAGE.set(0)
    ACTIVE_CONNECTIONS.set(0)
    
    logger.info("Monitoring setup complete")
"""
Rate limiting for Supadata API calls to minimize costs and avoid throttling
"""

import time
import threading
from typing import Optional
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)


class SupadataRateLimiter:
    """Rate limiter for Supadata API calls"""
    
    def __init__(
        self,
        requests_per_minute: int = None,
        requests_per_hour: int = None,
        min_request_interval: float = None
    ):
        # Load from environment or use defaults
        self.requests_per_minute = requests_per_minute or int(os.getenv("SUPADATA_REQUESTS_PER_MINUTE", "30"))
        self.requests_per_hour = requests_per_hour or int(os.getenv("SUPADATA_REQUESTS_PER_HOUR", "500"))
        self.min_request_interval = min_request_interval or float(os.getenv("SUPADATA_MIN_INTERVAL", "1.0"))
        
        # Tracking
        self.last_request_time = None
        self.minute_requests = []
        self.hour_requests = []
        self.lock = threading.Lock()
        
        logger.info(f"Supadata rate limiter: {self.requests_per_minute}/min, {self.requests_per_hour}/hr, min interval: {self.min_request_interval}s")
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits"""
        with self.lock:
            now = datetime.now()
            
            # Clean old requests
            self._cleanup_old_requests(now)
            
            # Check rate limits
            wait_time = 0
            
            # Check minimum interval
            if self.last_request_time:
                time_since_last = (now - self.last_request_time).total_seconds()
                if time_since_last < self.min_request_interval:
                    wait_time = max(wait_time, self.min_request_interval - time_since_last)
            
            # Check per-minute limit
            if len(self.minute_requests) >= self.requests_per_minute:
                oldest_minute_request = min(self.minute_requests)
                time_until_reset = 60 - (now - oldest_minute_request).total_seconds()
                if time_until_reset > 0:
                    wait_time = max(wait_time, time_until_reset + 0.1)
                    logger.warning(f"Per-minute rate limit reached, waiting {time_until_reset:.1f}s")
            
            # Check per-hour limit
            if len(self.hour_requests) >= self.requests_per_hour:
                oldest_hour_request = min(self.hour_requests)
                time_until_reset = 3600 - (now - oldest_hour_request).total_seconds()
                if time_until_reset > 0:
                    wait_time = max(wait_time, time_until_reset + 0.1)
                    logger.warning(f"Per-hour rate limit reached, waiting {time_until_reset/60:.1f}min")
            
            # Wait if necessary
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.1f}s before Supadata request")
                time.sleep(wait_time)
                now = datetime.now()  # Update now after waiting
            
            # Record this request
            self.minute_requests.append(now)
            self.hour_requests.append(now)
            self.last_request_time = now
    
    def _cleanup_old_requests(self, now: datetime) -> None:
        """Remove request timestamps outside the tracking windows"""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        self.minute_requests = [req_time for req_time in self.minute_requests if req_time > minute_ago]
        self.hour_requests = [req_time for req_time in self.hour_requests if req_time > hour_ago]
    
    def get_stats(self) -> dict:
        """Get current rate limiting stats"""
        with self.lock:
            now = datetime.now()
            self._cleanup_old_requests(now)
            
            return {
                "requests_last_minute": len(self.minute_requests),
                "requests_last_hour": len(self.hour_requests),
                "minute_limit": self.requests_per_minute,
                "hour_limit": self.requests_per_hour,
                "last_request": self.last_request_time.isoformat() if self.last_request_time else None,
                "min_interval": self.min_request_interval
            }


# Global rate limiter instance
_global_rate_limiter = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> SupadataRateLimiter:
    """Get or create the global rate limiter instance"""
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        with _limiter_lock:
            if _global_rate_limiter is None:
                _global_rate_limiter = SupadataRateLimiter()
    
    return _global_rate_limiter


def rate_limited_supadata_call(func):
    """Decorator to apply rate limiting to Supadata API calls"""
    def wrapper(*args, **kwargs):
        rate_limiter = get_rate_limiter()
        rate_limiter.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper
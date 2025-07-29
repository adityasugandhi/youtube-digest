import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """No-op cache manager (Redis disabled)"""
    
    def __init__(self):
        logger.info("Cache disabled - using no-op cache manager")
        self.enabled = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value - always returns None (no caching)"""
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set cached value - no-op (no caching)"""
        pass
    
    async def delete(self, key: str):
        """Delete cached value - no-op (no caching)"""
        pass


# Global cache manager instance
cache_manager = CacheManager()


async def get_cached_result(key: str) -> Optional[Any]:
    """Get cached result"""
    return await cache_manager.get(key)


async def cache_result(key: str, value: Any, ttl: int = None):
    """Cache result"""
    await cache_manager.set(key, value, ttl)
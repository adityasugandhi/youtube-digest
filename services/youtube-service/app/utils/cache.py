import redis
import pickle
import logging
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis-based caching manager"""
    
    def __init__(self):
        try:
            self.redis = redis.Redis.from_url(settings.redis_url)
            # Test connection
            self.redis.ping()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if not self.redis:
            return None
            
        try:
            value = self.redis.get(key)
            if value:
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set cached value with TTL"""
        if not self.redis:
            return
            
        try:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis.setex(key, ttl, serialized)
            else:
                self.redis.setex(key, settings.redis_cache_ttl, serialized)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete cached value"""
        if not self.redis:
            return
            
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")


# Global cache manager instance
cache_manager = CacheManager()


async def get_cached_result(key: str) -> Optional[Any]:
    """Get cached result"""
    return await cache_manager.get(key)


async def cache_result(key: str, value: Any, ttl: int = None):
    """Cache result"""
    await cache_manager.set(key, value, ttl)
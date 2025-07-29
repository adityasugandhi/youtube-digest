from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from typing import Optional
import time
from datetime import datetime, timedelta
import logging

from app.services.youtube_client import YouTubeClient
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}


def get_youtube_client() -> YouTubeClient:
    """Dependency to get YouTube client"""
    return YouTubeClient()


async def rate_limit(request: Request) -> None:
    """Rate limiting dependency"""
    client_ip = request.client.host
    current_time = datetime.now()
    
    # Clean old entries
    if client_ip in rate_limit_storage:
        rate_limit_storage[client_ip] = [
            timestamp for timestamp in rate_limit_storage[client_ip]
            if (current_time - timestamp).seconds < settings.rate_limit_window
        ]
    else:
        rate_limit_storage[client_ip] = []
    
    # Check rate limit
    if len(rate_limit_storage[client_ip]) >= settings.rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Add current request
    rate_limit_storage[client_ip].append(current_time)


async def verify_api_key(authorization=Depends(security)) -> Optional[str]:
    """Verify API key (optional for development)"""
    if settings.environment == "development":
        return "dev-key"
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # In production, verify against database or environment
    # For now, just check if it exists
    if not authorization.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return authorization.credentials
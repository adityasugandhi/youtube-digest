from fastapi import Depends, HTTPException, Request, status
from typing import Optional, Annotated
import time
from datetime import datetime, timedelta
import logging

from app.services.digest_generator import RobinhoodDigestGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}


def get_digest_generator() -> RobinhoodDigestGenerator:
    """Dependency to get digest generator"""
    return RobinhoodDigestGenerator()


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
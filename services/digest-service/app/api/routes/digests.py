from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
import logging
import sys
import os

# Add shared schemas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../shared'))
from schemas.common import DigestRequest, DigestResponse

from app.services.digest_generator import RobinhoodDigestGenerator
from app.api.dependencies import get_digest_generator, rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=DigestResponse)
async def generate_digest(
    request: DigestRequest,
    digest_generator: RobinhoodDigestGenerator = Depends(get_digest_generator),
    _: None = Depends(rate_limit)
):
    """Generate a single Robinhood-style digest from transcript"""
    
    try:
        logger.info(f"Generating digest for video {request.video_id}")
        
        # Generate digest
        digest = await digest_generator.generate_digest(request)
        
        logger.info(f"Generated digest for video {request.video_id} with quality score {digest.quality_score}")
        
        return digest
        
    except Exception as e:
        logger.error(f"Error generating digest for video {request.video_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch", response_model=List[DigestResponse])
async def generate_batch_digests(
    requests: List[DigestRequest],
    digest_generator: RobinhoodDigestGenerator = Depends(get_digest_generator),
    _: None = Depends(rate_limit)
):
    """Generate multiple digests concurrently"""
    
    if len(requests) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 digest requests per batch"
        )
    
    try:
        logger.info(f"Generating batch of {len(requests)} digests")
        
        # Generate digests
        digests = await digest_generator.batch_generate_digests(requests)
        
        successful_count = sum(1 for d in digests if not d.error)
        logger.info(f"Generated {successful_count}/{len(requests)} digests successfully")
        
        return digests
        
    except Exception as e:
        logger.error(f"Error generating batch digests: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{digest_id}")
async def get_digest(
    digest_id: str,
    _: None = Depends(rate_limit)
):
    """Get a digest by ID (placeholder - would require database implementation)"""
    
    return {
        "digest_id": digest_id,
        "message": "Digest retrieval endpoint - requires database implementation"
    }
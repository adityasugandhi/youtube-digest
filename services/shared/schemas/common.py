from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class TranscriptSegment(BaseModel):
    """Individual transcript segment"""
    text: str
    start: float
    duration: float
    end: float


class StreamInfo(BaseModel):
    """YouTube stream information"""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: str
    duration: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None


class TranscriptResponse(BaseModel):
    """Response for transcript extraction"""
    video_id: str
    transcript: List[TranscriptSegment]
    segment_count: int
    total_duration: float
    language: str = "en"
    is_auto_generated: bool = True


class BatchTranscriptRequest(BaseModel):
    """Request for batch transcript extraction"""
    video_ids: List[str] = Field(..., max_length=20)
    concurrent_limit: Optional[int] = Field(default=5, ge=1, le=10)


class BatchTranscriptResponse(BaseModel):
    """Response for batch transcript extraction"""
    successful: List[TranscriptResponse]
    failed: List[Dict[str, str]]
    total_requested: int
    successful_count: int
    failed_count: int


class BulletPoint(BaseModel):
    """Individual bullet point in digest"""
    text: str
    word_count: int
    has_numbers: bool


class DigestRequest(BaseModel):
    """Request for digest generation"""
    video_id: str
    transcript: str
    metadata: Dict[str, Any]
    focus_areas: Optional[str] = None
    ai_providers: Optional[List[str]] = ["openai"]


class DigestResponse(BaseModel):
    """Response for digest generation"""
    video_id: str
    title: str
    bullet_points: List[BulletPoint]
    raw_digest: str
    quality_score: float
    ai_model: str
    tokens_used: int
    processing_time: float
    confidence_score: float
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: float
    service: Optional[str] = None
    version: Optional[str] = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response"""
    status: str
    checks: Dict[str, bool]
    timestamp: float
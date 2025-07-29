from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class StreamRecord(Base):
    """YouTube stream record"""
    __tablename__ = "streams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(String(20), unique=True, index=True, nullable=False)
    channel_id = Column(String(30), index=True, nullable=False)
    channel_title = Column(String(200))
    title = Column(String(500))
    description = Column(Text)
    published_at = Column(DateTime, index=True)
    duration = Column(Integer)  # seconds
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    actual_start_time = Column(DateTime)
    actual_end_time = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    transcript = relationship("TranscriptRecord", back_populates="stream", uselist=False)
    digests = relationship("DigestRecord", back_populates="stream")
    
    # Add composite indexes for common queries
    __table_args__ = (
        Index('idx_channel_published', 'channel_id', 'published_at'),
        Index('idx_view_count_desc', 'view_count', postgresql_using='btree'),
        Index('idx_created_at', 'created_at'),
    )


class TranscriptRecord(Base):
    """Transcript record"""
    __tablename__ = "transcripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(String(20), ForeignKey('streams.video_id'), unique=True, index=True, nullable=False)
    transcript_data = Column(JSON)  # List of transcript segments
    segment_count = Column(Integer)
    total_duration = Column(Float)
    language = Column(String(10), default='en')
    is_auto_generated = Column(Boolean, default=True)
    
    # Metadata
    extracted_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    stream = relationship("StreamRecord", back_populates="transcript")
    
    # Indexes
    __table_args__ = (
        Index('idx_extracted_at', 'extracted_at'),
        Index('idx_language', 'language'),
    )


class DigestRecord(Base):
    """AI-generated digest record"""
    __tablename__ = "digests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(String(20), ForeignKey('streams.video_id'), index=True, nullable=False)
    title = Column(String(200))
    bullet_points = Column(JSON)  # List of bullet point objects
    raw_digest = Column(Text)
    quality_score = Column(Float)
    ai_model = Column(String(50))
    tokens_used = Column(Integer)
    processing_time = Column(Float)
    confidence_score = Column(Float)
    
    # Metadata
    metadata = Column(JSON)  # Additional metadata
    generated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Error tracking
    error_message = Column(Text)
    
    # Relationships
    stream = relationship("StreamRecord", back_populates="digests")
    
    # Indexes
    __table_args__ = (
        Index('idx_video_generated', 'video_id', 'generated_at'),
        Index('idx_quality_score', 'quality_score'),
        Index('idx_ai_model', 'ai_model'),
    )


class ProcessingJobRecord(Base):
    """Processing job tracking"""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False)  # 'transcript', 'digest', 'batch'
    status = Column(String(20), default='pending')  # 'pending', 'running', 'completed', 'failed'
    
    # Job parameters
    parameters = Column(JSON)
    
    # Progress tracking
    total_items = Column(Integer)
    completed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Error tracking
    error_message = Column(Text)
    
    # Indexes
    __table_args__ = (
        Index('idx_job_type_status', 'job_type', 'status'),
        Index('idx_created_at_desc', 'created_at', postgresql_using='btree'),
    )


class ApiKeyRecord(Base):
    """API key management"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100))
    description = Column(Text)
    
    # Usage tracking
    requests_made = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Limits
    rate_limit = Column(Integer, default=100)  # requests per hour
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime)
    
    # Indexes
    __table_args__ = (
        Index('idx_active_keys', 'is_active'),
        Index('idx_expires_at', 'expires_at'),
    )


class MetricsRecord(Base):
    """Application metrics storage"""
    __tablename__ = "metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(20))  # 'counter', 'gauge', 'histogram'
    
    # Labels/dimensions
    labels = Column(JSON)
    
    # Timestamp
    timestamp = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_metric_name_timestamp', 'metric_name', 'timestamp'),
        Index('idx_timestamp_desc', 'timestamp', postgresql_using='btree'),
    )
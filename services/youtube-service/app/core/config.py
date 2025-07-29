from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App Configuration
    app_name: str = "YouTube Digest Service"
    version: str = "1.0.0"
    debug: bool = False
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # YouTube API
    youtube_api_key: str
    youtube_api_quota_limit: int = 10000
    
    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis (disabled)
    # redis_url: str = "redis://localhost:6379"
    # redis_cache_ttl: int = 3600  # 1 hour
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 500
    openai_temperature: float = 0.3
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    # Monitoring
    sentry_dsn: str = ""
    log_level: str = "INFO"
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
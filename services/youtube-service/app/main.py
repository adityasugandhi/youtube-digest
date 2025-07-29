from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import time
import logging
import sys
import os

# Add paths to sys.path for proper imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, 'services/shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from schemas.common import HealthResponse
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import transcripts, streams
from app.utils.monitoring import setup_monitoring

# Setup logging
setup_logging()
logger = logging.getLogger("youtube-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    await setup_monitoring()
    
    yield
    
    # Shutdown
    logger.info("Shutting down YouTube Service")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="YouTube Live Stream Transcript Extraction Service",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["yourapp.com", "api.yourapp.com"]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": request.url.path
        }
    )


# Health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.version,
        timestamp=time.time()
    )


# Include routers
app.include_router(
    transcripts.router,
    prefix=f"{settings.api_v1_prefix}/transcripts",
    tags=["transcripts"]
)

app.include_router(
    streams.router,
    prefix=f"{settings.api_v1_prefix}/streams",
    tags=["streams"]
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
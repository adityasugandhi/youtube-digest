FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies needed for insights endpoint
RUN pip install --no-cache-dir groq

# Copy application files
COPY *.py ./
COPY youtube_creators_list.json ./

# Create non-root user and set permissions
RUN useradd --create-home --shell /bin/bash automation \
    && mkdir -p /var/log/youtube-automation \
    && chown -R automation:automation /app /var/log/youtube-automation

# Switch to non-root user
USER automation

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_DIR=/var/log/youtube-automation

# Expose API port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the FastAPI insights API directly
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8003"]
# Multi-stage build for minimal ASR service
# Stage 1: Builder - compile dependencies
FROM python:3.9-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    transformers==4.30.0 \
    librosa==0.10.0 \
    soundfile==0.12.1 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.0 \
    python-multipart==0.0.6 \
    python-dotenv==1.0.0 \
    google-cloud-storage==2.10.0 \
    psutil==5.9.0 \
    requests==2.31.0

# Stage 2: Runtime - minimal production image  
FROM python:3.9-slim AS runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory and create it
WORKDIR /app

# Copy only application code (no models included)
COPY *.py ./
COPY startup.sh ./startup.sh
RUN chmod +x ./startup.sh

# Create lightweight cache directories
RUN mkdir -p /tmp/model_cache

# Optimized environment variables
ENV PYTHONPATH=/app
ENV MODEL_CACHE_DIR=/tmp/model_cache
ENV TRANSFORMERS_CACHE=/tmp/model_cache/transformers
ENV HUGGINGFACE_HUB_CACHE=/tmp/model_cache/hub
ENV HF_HOME=/tmp/model_cache/hf
ENV TORCH_HOME=/tmp/model_cache/torch

# Production configuration - auto-detect GPU availability
ENV GPU_SUPPORT=auto
ENV MODEL_CACHE_SIZE=3
ENV TRANSFORMERS_OFFLINE=0
ENV HF_DATASETS_OFFLINE=0

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash asr \
    && chown -R asr:asr /app /tmp/model_cache
USER asr

# Expose port
EXPOSE 8004

# Lightweight health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8004/health', timeout=5)" || exit 1

# Run the application
CMD ["./startup.sh"]
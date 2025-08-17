# Accept build argument for GPU support
ARG GPU_SUPPORT=cpu

# Multi-stage build with GCP optimizations
FROM gcr.io/deeplearning-platform-release/pytorch-gpu.1-13:latest as gpu-builder
FROM gcr.io/distroless/python3-debian11:latest as cpu-base

# Builder stage for GPU
FROM gpu-builder as gpu-deps
WORKDIR /app
COPY requirements.txt .

# Install only additional packages not in GCP base
RUN pip install --no-cache-dir --target=/install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    python-multipart==0.0.6 \
    transformers>=4.30.0 \
    librosa>=0.10.0 \
    python-dotenv==1.0.0

# Final GPU stage using GCP optimized base
FROM gcr.io/deeplearning-platform-release/pytorch-gpu.1-13:latest as gpu-final
WORKDIR /app
COPY --from=gpu-deps /install /usr/local/lib/python3.8/site-packages/
COPY . .
ENV GPU_SUPPORT=cuda
EXPOSE 8004
CMD ["python", "main.py"]

# CPU stage using distroless
FROM cpu-base as cpu-final
WORKDIR /app
COPY requirements.txt .
# Install to custom location for distroless
RUN ["python", "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"]
COPY . .
ENV GPU_SUPPORT=cpu
EXPOSE 8004
CMD ["python", "main.py"]

# Final stage selection
FROM ${GPU_SUPPORT}-final as final

# Copy application code
COPY . .

# Set environment variable for runtime GPU detection
ENV GPU_SUPPORT=${GPU_SUPPORT}

# Expose port
EXPOSE 8004

# Run the application
CMD ["python", "main.py"]
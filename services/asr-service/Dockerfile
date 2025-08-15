FROM python:3.11-slim

# Accept build argument for GPU support
ARG GPU_SUPPORT=cpu

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies based on GPU support
RUN if [ "$GPU_SUPPORT" = "metal" ]; then \
        echo "Installing Apple Metal GPU optimized packages..."; \
        pip install --no-cache-dir -r requirements.txt; \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    elif [ "$GPU_SUPPORT" = "cuda" ]; then \
        echo "Installing CUDA GPU optimized packages..."; \
        pip install --no-cache-dir -r requirements.txt; \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118; \
    else \
        echo "Installing CPU-only packages..."; \
        pip install --no-cache-dir -r requirements.txt; \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Copy application code
COPY . .

# Set environment variable for runtime GPU detection
ENV GPU_SUPPORT=${GPU_SUPPORT}

# Expose port
EXPOSE 8004

# Run the application
CMD ["python", "main.py"]
# Multi-stage build for React app with Python backend
FROM node:18-alpine as react-builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Python backend stage
FROM python:3.11-slim

# Set build arguments
ARG BUILD_DATE
ARG VERSION=latest

# Set build labels
LABEL maintainer="Munshi Team <team@munshi.dev>"
LABEL version=${VERSION}
LABEL build-date=${BUILD_DATE}
LABEL description="UI Service - React frontend with Python backend for Munshi"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r munshi && useradd -r -g munshi -u 1000 munshi

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built React app
COPY --from=react-builder /app/dist ./dist

# Copy server
COPY server.py .

# Set ownership
RUN chown -R munshi:munshi /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Switch to non-root user
USER munshi

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "server.py"]
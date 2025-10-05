#!/bin/bash
set -e

echo "🚀 Starting ASR Service with model pre-loading..."

# Check if we should pre-load models
PRELOAD_MODELS=${PRELOAD_MODELS:-"true"}
STARTUP_TIMEOUT=${STARTUP_TIMEOUT:-"300"}

if [ "$PRELOAD_MODELS" = "true" ]; then
    echo "📦 Pre-loading models to reduce cold start time..."
    
    # Run model pre-loading with timeout
    timeout $STARTUP_TIMEOUT python preload-models.py || {
        echo "⚠️  Model pre-loading timed out or failed, starting without pre-loaded models"
    }
else
    echo "⏭️  Skipping model pre-loading (PRELOAD_MODELS=false)"
fi

echo "🎯 Starting ASR service..."
exec python main.py
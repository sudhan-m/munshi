#!/bin/bash

echo "🧹 Cleaning Munshi UI Service..."

# Remove build artifacts
rm -rf dist/ build/ .cache/ .vite/

# Remove dependencies
rm -rf node_modules/ venv/

# Remove logs
rm -f *.log
rm -rf logs/

# Remove Python cache
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Cleanup complete!"
echo "Run './dev.sh' to reinstall dependencies and start development"
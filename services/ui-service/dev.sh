#!/bin/bash
set -e

echo "🚀 Starting Munshi UI Service in development mode..."

# Install dependencies
[ ! -d "node_modules" ] && echo "📦 Installing React dependencies..." && npm install
[ ! -d "venv" ] && echo "🐍 Setting up Python environment..." && python3 -m venv venv
source venv/bin/activate && pip install -q -r requirements.txt

# Cleanup function
cleanup() {
    echo "🛑 Shutting down services..."
    kill $REACT_PID $PYTHON_PID 2>/dev/null || true
    wait
}
trap cleanup SIGINT SIGTERM EXIT

# Start services
echo "🐍 Starting Python backend (port 8002)..."
python server.py &
PYTHON_PID=$!

echo "⚛️  Starting React frontend (port 3000)..."
npm run dev &
REACT_PID=$!

echo "✅ Services started:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8002"
echo "   Press Ctrl+C to stop"

wait
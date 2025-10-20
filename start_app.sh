#!/bin/bash

# AI RFP Assistant Startup Script
# This script properly activates the virtual environment and starts the application

echo "🚀 Starting AI RFP Assistant..."

# Change to project directory
cd "$(dirname "$0")"

# If already in a virtualenv, use it; otherwise prefer ./venv bin without sourcing
if [ -z "$VIRTUAL_ENV" ]; then
  if [ ! -d "venv" ]; then
      echo "❌ Virtual environment not found. Please run setup first."
      exit 1
  fi
  VENV_BIN="$(pwd)/venv/bin"
else
  VENV_BIN="$(dirname \"$VIRTUAL_ENV\")/bin"
fi

# Check if chainlit is installed
if ! "$VENV_BIN/python" -c "import chainlit" 2>/dev/null; then
    echo "❌ Chainlit not found in virtual environment. Installing dependencies..."
    "$VENV_BIN/pip" install -r requirements.txt
fi

# Start FastAPI backend in background
echo "🌐 Starting FastAPI backend..."
"$VENV_BIN/python" fastapi_backend.py &  # runs on port 8001
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

# Start Chainlit frontend
echo "🎨 Starting Chainlit frontend..."
echo "📱 UI http://localhost:8000  |  API http://localhost:8001"
echo "🛑 Press Ctrl+C to stop the application"

# Function to cleanup on exit (kill entire process group)
cleanup() {
    echo "🛑 Shutting down..."
    # Kill FastAPI if still running
    if ps -p $FASTAPI_PID > /dev/null 2>&1; then
        kill $FASTAPI_PID 2>/dev/null
    fi
    # Kill all child processes in this process group
    pkill -P $$ 2>/dev/null
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start Chainlit
"$VENV_BIN/chainlit" run main.py --port 8000 --host 0.0.0.0

#!/bin/bash

set -e

echo "🚀 RFP Tool - Auto Startup Script"
echo "=================================="

find_python() {
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD=python3.11
        VERSION=$(python3.11 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
        echo "✅ Using Python $VERSION"
        return 0
    fi
    
    echo "❌ Python 3.11 not found."
    echo ""
    echo "This tool requires exactly Python 3.11."
    echo "Please install it:"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu/Debian: apt install python3.11"
    echo ""
    exit 1
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null 2>&1; then
        echo "❌ Docker daemon not running. Please start Docker."
        exit 1
    fi
    
    echo "✅ Docker is running"
}

start_storage() {
    echo ""
    echo "📦 Starting local storage services..."
    
    if docker ps | grep -q rfp-tool-minio; then
        echo "✅ MinIO already running"
    else
        echo "🔄 Starting MinIO..."
        docker-compose up -d 2>&1 | grep -v "orphan" || true
        
        echo "⏳ Waiting for MinIO to be ready..."
        sleep 5
        
        for i in {1..10}; do
            if docker exec rfp-tool-minio curl -f http://localhost:9000/minio/health/live &> /dev/null; then
                echo "✅ MinIO is ready"
                break
            fi
            if [ $i -eq 10 ]; then
                echo "⚠️  MinIO taking longer than expected, but continuing..."
            else
                sleep 2
            fi
        done
    fi
}

create_directories() {
    echo ""
    echo "📁 Creating necessary directories..."
    mkdir -p .data/proposals
    mkdir -p .data/diagrams
    echo "✅ Directories created"
}

check_env() {
    echo ""
    echo "🔧 Checking configuration..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            echo "⚠️  No .env file found. Creating from .env.example..."
            cp .env.example .env
            echo "📝 Edit .env file with your API keys (or leave blank for Ollama)"
        else
            echo "⚠️  No .env file found. Using defaults (Ollama)"
        fi
    else
        echo "✅ Configuration file found"
    fi
}

setup_venv() {
    echo ""
    echo "🐍 Setting up Python environment..."
    
    # Check if venv exists
    if [ -d "venv" ]; then
        echo "✅ Virtual environment found"
        
        # Activate existing venv
        source venv/bin/activate
        
        # Verify venv is working
        if ! python -c "import sys" &> /dev/null; then
            echo "⚠️  Virtual environment appears corrupted, recreating..."
            deactivate 2>/dev/null || true
            rm -rf venv
            $PYTHON_CMD -m venv venv
            source venv/bin/activate
            echo "🔄 Upgrading pip in new venv..."
            pip install --upgrade pip -q
            FORCE_INSTALL=1
        else
            echo "✅ Virtual environment activated"
        fi
    else
        echo "🔄 Creating new virtual environment with $PYTHON_CMD..."
        $PYTHON_CMD -m venv venv
        source venv/bin/activate
        echo "🔄 Upgrading pip in new venv..."
        pip install --upgrade pip -q
        FORCE_INSTALL=1
    fi
    
    # Check if requirements have changed
    REQUIREMENTS_HASH=$(shasum requirements.txt 2>/dev/null | awk '{print $1}')
    STORED_HASH=""
    
    if [ -f ".venv_requirements_hash" ]; then
        STORED_HASH=$(cat .venv_requirements_hash)
    fi
    
    if [ "$FORCE_INSTALL" = "1" ]; then
        echo "📦 Installing dependencies (this may take a minute)..."
        pip install -r requirements.txt -q
        echo "$REQUIREMENTS_HASH" > .venv_requirements_hash
        echo "✅ All dependencies installed"
    elif [ "$REQUIREMENTS_HASH" != "$STORED_HASH" ]; then
        echo "📦 Requirements changed, updating dependencies..."
        pip install -r requirements.txt -q
        echo "$REQUIREMENTS_HASH" > .venv_requirements_hash
        echo "✅ Dependencies updated"
    else
        echo "✅ Dependencies up to date (skipping installation)"
    fi
}

start_app() {
    echo ""
    echo "🚀 Starting RFP Tool..."
    echo ""
    echo "⏳ Initializing components (LLM, Storage, Agents)..."
    echo "   This may take 20-30 seconds on first startup..."
    echo ""
    
    source venv/bin/activate
    chainlit run app.py --host localhost --port 8000 -h &
    
    echo ""
    echo "⏳ Waiting for server to start..."
    sleep 25
    
    echo ""
    echo "================================================"
    echo "✅ RFP Tool is ready!"
    echo ""
    echo "Chainlit UI: http://localhost:8000"
    echo "MinIO Console: http://localhost:9001 (optional)"
    echo "================================================"
    echo ""
    echo "💡 Type /help in the chat to see available commands"
    echo "💡 Press Ctrl+C to stop the server"
    echo ""
    
    wait
}

main() {
    find_python
    check_docker
    start_storage
    create_directories
    check_env
    setup_venv
    start_app
}

main


#!/usr/bin/env python3
"""
Setup script for the AI RFP Assistant.
Handles virtual environment creation, dependency installation, and service verification.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run(cmd, timeout=300):
    """Run a shell command and print it before execution with timeout."""
    print(f"\n> {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after {timeout} seconds: {cmd}")
        raise
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}: {cmd}")
        raise

def ensure_virtualenv():
    """Ensure a single project virtualenv at ./venv; respect existing active VIRTUAL_ENV.

    - If $VIRTUAL_ENV is already set, use it (no nesting).
    - Otherwise, create ./venv if missing and prepend its bin/Scripts to PATH for subprocesses.
    """
    # Respect an already active virtual environment
    current_venv = os.environ.get("VIRTUAL_ENV")
    if current_venv:
        print(f"✅ Using active virtual environment: {current_venv}")
        return

    venv_dir = Path("venv")
    try:
        if venv_dir.exists():
            print("✅ Virtual environment found at ./venv")
        else:
            print("⚙️ Creating virtual environment at ./venv ...")
            run(f"{sys.executable} -m venv venv")
    except Exception as e:
        print(f"❌ Error creating virtual environment: {e}")
        sys.exit(1)

    activate_script = "Scripts/activate" if platform.system() == "Windows" else "bin/activate"
    activate_path = venv_dir / activate_script

    if not activate_path.exists():
        print(f"❌ Error: activation script not found at {activate_path}")
        sys.exit(1)

    # Configure environment for subprocesses without sourcing in parent shell
    try:
        if platform.system() == "Windows":
            os.environ["VIRTUAL_ENV"] = str(venv_dir.resolve())
            os.environ["PATH"] = f"{venv_dir / 'Scripts'};" + os.environ.get("PATH", "")
        else:
            os.environ["VIRTUAL_ENV"] = str(venv_dir.resolve())
            os.environ["PATH"] = f"{venv_dir / 'bin'}:" + os.environ.get("PATH", "")
    except Exception as e:
        print(f"❌ Error configuring environment variables: {e}")
        sys.exit(1)


def install_requirements():
    """Install project dependencies from requirements.txt."""
    print("📦 Installing dependencies...")
    run("pip install --upgrade pip")
    run("pip install -r requirements.txt")


def check_ollama():
    """Check if Ollama is installed and running."""
    print("🔍 Checking Ollama installation...")
    try:
        # Check if ollama command exists
        result = subprocess.run("ollama --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama is installed")
            print(f"   Version: {result.stdout.strip()}")
        else:
            print("❌ Ollama is not installed")
            print("   Please install Ollama from https://ollama.com/")
            return False
    except FileNotFoundError:
        print("❌ Ollama is not installed")
        print("   Please install Ollama from https://ollama.com/")
        return False
    
    # Check if Ollama service is running
    try:
        # Use curl to check Ollama service directly
        result = subprocess.run(["curl", "-s", "http://localhost:11434/api/tags"], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            try:
                data = json.loads(result.stdout)
                models = data.get("models", [])
                model_names = [model["name"] for model in models]
                
                print("✅ Ollama service is running")
                print(f"   Available models: {', '.join(model_names)}")
                
                # Check for Qwen models
                qwen_models = [name for name in model_names if "qwen" in name.lower()]
                if qwen_models:
                    print(f"✅ Found Qwen models: {', '.join(qwen_models)}")
                    if "qwen3:4b" in model_names:
                        print("✅ Qwen3:4B model is available")
                        return True
                    else:
                        print("⚠️  Qwen3:4B model not found, but other Qwen models available")
                        print("   Run: ollama pull qwen3:4b")
                        return False
                else:
                    print("⚠️  No Qwen models found")
                    print("   Run: ollama pull qwen3:4b")
                    return False
            except json.JSONDecodeError:
                print("❌ Invalid response from Ollama service")
                return False
        else:
            print("❌ Ollama service is not running")
            print("   Run: ollama serve")
            return False
            
    except Exception as e:
        print(f"❌ Cannot connect to Ollama service: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return False


def check_docker_services():
    """Check if Docker services (DynamoDB Local and MinIO) are running."""
    print("🔍 Checking Docker services...")
    
    # Check if Docker is running
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ Docker is not running or not installed")
            print("   Please start Docker Desktop or install Docker")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        print("   Please install Docker from https://docker.com/")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Docker command timed out")
        return False
    
    # Check DynamoDB Local
    try:
        result = subprocess.run(["curl", "-s", "http://localhost:8000"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ DynamoDB Local is running")
        else:
            print("⚠️  DynamoDB Local is not running")
            print("   Run: docker-compose up -d dynamodb-local")
            return False
    except Exception as e:
        print(f"⚠️  Cannot connect to DynamoDB Local: {e}")
        print("   Run: docker-compose up -d dynamodb-local")
        return False
    
    # Check MinIO
    try:
        result = subprocess.run(["curl", "-s", "http://localhost:9000/minio/health/live"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ MinIO is running")
        else:
            print("⚠️  MinIO is not running")
            print("   Run: docker-compose up -d minio")
            return False
    except Exception as e:
        print(f"⚠️  Cannot connect to MinIO: {e}")
        print("   Run: docker-compose up -d minio")
        return False
    
    return True


def setup_local_services():
    """Setup local services (DynamoDB and MinIO) if not running."""
    print("🔧 Setting up local services...")
    
    try:
        # Start Docker services
        print("📦 Starting Docker services...")
        subprocess.run(["docker-compose", "up", "-d", "dynamodb-local", "minio"], 
                      check=True, timeout=60)
        
        # Wait a bit for services to start
        import time
        time.sleep(5)
        
        # Verify services are running
        if check_docker_services():
            print("✅ Local services are running")
            return True
        else:
            print("❌ Failed to start local services")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Docker services: {e}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Docker services startup timed out")
        return False
    except Exception as e:
        print(f"❌ Unexpected error starting services: {e}")
        return False


def main():
    """Run project setup."""
    print("\n=== AI RFP Assistant Setup ===")
    ensure_virtualenv()
    install_requirements()
    
    # Check Ollama setup
    if not check_ollama():
        print("\n⚠️  Ollama setup incomplete. Please:")
        print("   1. Install Ollama: https://ollama.com/")
        print("   2. Start Ollama: ollama serve")
        print("   3. Pull model: ollama pull qwen3:4b")
        print("   4. Then run this script again")
        sys.exit(1)
    
    # Check Docker services
    if not check_docker_services():
        print("\n🔧 Setting up local services...")
        if not setup_local_services():
            print("\n⚠️  Local services setup failed. Please:")
            print("   1. Install Docker: https://docker.com/")
            print("   2. Start Docker Desktop")
            print("   3. Run: docker-compose up -d dynamodb-local minio")
            print("   4. Then run this script again")
            sys.exit(1)
    
    print("\n✅ Setup completed successfully!")
    print("You can now start the application with: python scripts/dev.py start")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Health check script for the AI RFP Assistant.
Checks if all required services are running properly.
"""

import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_requests_module():
    """Check if requests module is available."""
    try:
        import requests  # noqa: F401
        return True
    except ImportError:
        logger.error("❌ 'requests' not found. Install it with: pip install requests")
        return False


def check_services():
    """Check if required services are running."""
    if not check_requests_module():
        return False
    
    try:
        import requests
    except ImportError:
        logger.error("❌ 'requests' not found. Install it with: pip install requests")
        return False
    
    services = {
        "Ollama": "http://localhost:11434/api/tags",
        "DynamoDB Local": "http://localhost:8000",
        "MinIO": "http://localhost:9000/minio/health/live"
    }
    
    logger.info("🔍 Checking required services...")
    all_running = True
    
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 400]:  # 400 is OK for DynamoDB
                logger.info(f"✅ {service_name} is running")
            else:
                logger.warning(f"⚠️ {service_name} returned status {response.status_code}")
                all_running = False
        except Exception as e:
            logger.error(f"❌ {service_name} is not running: {e}")
            all_running = False
    
    return all_running


def check_ollama_models():
    """Check if required Ollama models are available."""
    try:
        import requests
        import json
        
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = json.loads(response.text)
            models = data.get("models", [])
            model_names = [model["name"] for model in models]
            
            logger.info(f"📋 Available models: {', '.join(model_names)}")
            
            # Check for Qwen models
            qwen_models = [name for name in model_names if "qwen" in name.lower()]
            if qwen_models:
                logger.info(f"✅ Found Qwen models: {', '.join(qwen_models)}")
                if "qwen3:4b" in model_names:
                    logger.info("✅ Qwen3:4B model is available")
                    return True
                else:
                    logger.warning("⚠️ Qwen3:4B model not found, but other Qwen models available")
                    logger.info("   Run: ollama pull qwen3:4b")
                    return False
            else:
                logger.warning("⚠️ No Qwen models found")
                logger.info("   Run: ollama pull qwen3:4b")
                return False
        else:
            logger.error("❌ Failed to get model list from Ollama")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking Ollama models: {e}")
        return False


def check_docker_services():
    """Check if Docker services are running."""
    import subprocess
    
    logger.info("🐳 Checking Docker services...")
    
    # Check if Docker is running
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error("❌ Docker is not running or not installed")
            logger.info("   Please start Docker Desktop or install Docker")
            return False
    except FileNotFoundError:
        logger.error("❌ Docker is not installed")
        logger.info("   Please install Docker from https://docker.com/")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Docker command timed out")
        return False
    
    # Check specific containers
    try:
        result = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("📋 Running Docker containers:")
            logger.info(result.stdout)
            
            # Check for required containers
            required_containers = ["dynamodb-local", "minio", "ollama"]
            running_containers = result.stdout.lower()
            
            for container in required_containers:
                if container in running_containers:
                    logger.info(f"✅ {container} container is running")
                else:
                    logger.warning(f"⚠️ {container} container is not running")
                    logger.info(f"   Run: docker-compose up -d {container}")
        else:
            logger.error("❌ Failed to list Docker containers")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking Docker containers: {e}")
        return False
    
    return True


def main():
    """Main health check function."""
    logger.info("🏥 AI RFP Assistant Health Check")
    logger.info("="*50)
    
    # Check services
    services_ok = check_services()
    
    # Check Ollama models
    models_ok = check_ollama_models()
    
    # Check Docker services
    docker_ok = check_docker_services()
    
    logger.info("="*50)
    
    if services_ok and models_ok and docker_ok:
        logger.info("✅ All services are healthy and ready!")
        logger.info("You can start the application with: python scripts/dev.py start")
        return True
    else:
        logger.warning("⚠️ Some services need attention:")
        if not services_ok:
            logger.warning("   - Service connectivity issues")
        if not models_ok:
            logger.warning("   - Ollama model issues")
        if not docker_ok:
            logger.warning("   - Docker service issues")
        logger.info("Run setup to fix issues: python scripts/dev.py setup")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

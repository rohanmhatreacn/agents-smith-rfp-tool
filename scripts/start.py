#!/usr/bin/env python3
"""
Startup script for the AI RFP Assistant.
This script starts both the FastAPI backend and Chainlit application.
"""

import subprocess
import sys
import time
import os
import signal
import logging
import socket
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _resolve_python_executable() -> str:
    """Return the best Python executable to use for child processes.

    Prefer the project's virtualenv at `venv/bin/python` if present; otherwise
    fall back to the current interpreter (sys.executable).
    """
    project_root = os.path.dirname(os.path.dirname(__file__))
    venv_python = os.path.join(project_root, "venv", "bin", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def _get_ports():
    """Get configured ports with defaults."""
    fastapi_port = int(os.getenv("FASTAPI_PORT", "8001"))
    chainlit_port = int(os.getenv("CHAINLIT_PORT", "8081"))
    return fastapi_port, chainlit_port

def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0

def _pid_on_port(port: int) -> int:
    """Return PID listening on the given port using lsof; 0 if none or not found."""
    try:
        result = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pid_str = result.stdout.strip().splitlines()[0]
            return int(pid_str)
    except Exception:
        pass
    return 0

def _kill_pid(pid: int):
    """Attempt to terminate a process by PID."""
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

def _http_ok(url: str, timeout: float = 3.0) -> bool:
    """Lightweight HTTP GET using urllib; return True on 2xx/4xx indicating service responds."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as e:
        return 200 <= e.code < 500
    except Exception:
        return False

def check_requests_module():
    """Check if requests module is available in the preferred Python env.

    We'll try importing with the resolved Python executable (prefer venv). If
    unavailable, log a warning but do not block startup.
    """
    exe = _resolve_python_executable()
    try:
        result = subprocess.run([exe, "-c", "import requests"], capture_output=True)
        if result.returncode == 0:
            return True
    except Exception:
        pass
    logger.info("ℹ️ Proceeding without 'requests' verification (using urllib for checks).")
    return True

def start_fastapi_backend():
    """Start the FastAPI backend server."""
    logger.info("🚀 Starting FastAPI backend server...")
    try:
        fastapi_port, _ = _get_ports()
        if _is_port_in_use(fastapi_port):
            # Verify health; if unhealthy, attempt restart
            if _http_ok(f"http://localhost:{fastapi_port}/health", timeout=3.0):
                logger.info("ℹ️ FastAPI port %d in use and healthy; skipping start.", fastapi_port)
                return None
            logger.warning("⚠️ FastAPI port %d in use but health check failed; attempting restart.", fastapi_port)
            pid = _pid_on_port(fastapi_port)
            if pid:
                logger.info("🔪 Terminating process %d on port %d", pid, fastapi_port)
                _kill_pid(pid)
        process = subprocess.Popen([
            _resolve_python_executable(), "-m", "uvicorn",
            "fastapi_backend:app",
            "--host", "0.0.0.0",
            "--port", str(fastapi_port),
            "--reload"
        ], cwd=os.path.dirname(os.path.dirname(__file__)))  # Go up one level to project root
        logger.info("✅ FastAPI backend started on port %d", fastapi_port)
        return process
    except Exception as e:
        logger.error(f"❌ Failed to start FastAPI backend: {e}")
        return None

def start_chainlit_app():
    """Start the Chainlit application."""
    logger.info("🚀 Starting Chainlit application...")
    try:
        _, chainlit_port = _get_ports()
        if _is_port_in_use(chainlit_port):
            # Verify health; if unhealthy, attempt restart
            if _http_ok(f"http://localhost:{chainlit_port}", timeout=3.0):
                logger.info("ℹ️ Chainlit port %d in use and healthy; skipping start.", chainlit_port)
                return None
            logger.warning("⚠️ Chainlit port %d in use but health check failed; attempting restart.", chainlit_port)
            pid = _pid_on_port(chainlit_port)
            if pid:
                logger.info("🔪 Terminating process %d on port %d", pid, chainlit_port)
                _kill_pid(pid)
        process = subprocess.Popen([
            _resolve_python_executable(), "-m", "chainlit", "run", "main.py",
            "--port", str(chainlit_port),
            "--host", "0.0.0.0"
        ], cwd=os.path.dirname(os.path.dirname(__file__)))  # Go up one level to project root
        logger.info("✅ Chainlit app started on port %d", chainlit_port)
        return process
    except Exception as e:
        logger.error(f"❌ Failed to start Chainlit app: {e}")
        return None

def check_services():
    """Check if required services are running."""
    if not check_requests_module():
        return False
    
    services = {
        "Ollama": "http://localhost:11434/api/tags",
        "DynamoDB Local": "http://localhost:8000",
        "MinIO": "http://localhost:9000/minio/health/live"
    }
    
    logger.info("🔍 Checking required services...")
    all_running = True
    
    for service_name, url in services.items():
        ok = _http_ok(url, timeout=3.0)
        if ok:
            logger.info(f"✅ {service_name} is responding")
        else:
            logger.warning(f"⚠️ {service_name} not responding at {url}")
            all_running = False
    
    return all_running

def main():
    """Main startup function."""
    logger.info("🎯 AI RFP Assistant Startup Script")
    logger.info("="*50)
    
    # Check if we're in the right directory (project root)
    project_root = os.path.dirname(os.path.dirname(__file__))
    main_py_path = os.path.join(project_root, "main.py")
    
    if not os.path.exists(main_py_path):
        logger.error("❌ main.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Check required services
    if not check_services():
        logger.warning("⚠️ Some required services are not running.")
        logger.info("Please ensure the following services are running:")
        logger.info("  - Ollama (port 11434)")
        logger.info("  - DynamoDB Local (port 8000)")
        logger.info("  - MinIO (port 9000)")
        logger.info("")
        logger.info("You can start them with: docker-compose up -d")
        logger.info("")
    
    # Start FastAPI backend (or detect existing)
    fastapi_process = start_fastapi_backend()
    if fastapi_process is None:
        fastapi_port, _ = _get_ports()
        # If not started by us, ensure it's actually responding
        if not _http_ok(f"http://localhost:{fastapi_port}/health", timeout=5.0):
            logger.error("❌ FastAPI backend not responding on port %d.", fastapi_port)
            sys.exit(1)
    
    # Wait a moment for FastAPI to start
    time.sleep(3)
    
    # Start Chainlit app (or detect existing)
    chainlit_process = start_chainlit_app()
    if chainlit_process is None:
        _, chainlit_port = _get_ports()
        # Best-effort ping of the Chainlit app root
        if not _http_ok(f"http://localhost:{chainlit_port}", timeout=5.0):
            logger.error("❌ Chainlit app not responding on port %d.", chainlit_port)
            if fastapi_process:
                fastapi_process.terminate()
            sys.exit(1)
    
    logger.info("="*50)
    logger.info("🎉 AI RFP Assistant is starting up!")
    logger.info("="*50)
    fastapi_port, chainlit_port = _get_ports()
    logger.info("📱 Chainlit App: http://localhost:%d", chainlit_port)
    logger.info("🔧 FastAPI Backend: http://localhost:%d", fastapi_port)
    logger.info("📚 API Documentation: http://localhost:%d/docs", fastapi_port)
    logger.info("="*50)
    logger.info("Press Ctrl+C to stop all services")
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("\n🛑 Shutting down services...")
        # Terminate gracefully
        if fastapi_process and fastapi_process.poll() is None:
            fastapi_process.terminate()
        if chainlit_process and chainlit_process.poll() is None:
            chainlit_process.terminate()
        # Wait briefly and force kill if needed
        time.sleep(2)
        if fastapi_process and fastapi_process.poll() is None:
            fastapi_process.kill()
        if chainlit_process and chainlit_process.poll() is None:
            chainlit_process.kill()
        logger.info("✅ All services stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Wait for processes
        while True:
            # If we spawned processes, monitor them. If we detected existing services, just periodically re-check health.
            if fastapi_process is not None and fastapi_process.poll() is not None:
                logger.error("❌ FastAPI backend stopped unexpectedly")
                break
            if chainlit_process is not None and chainlit_process.poll() is not None:
                logger.error("❌ Chainlit app stopped unexpectedly")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()

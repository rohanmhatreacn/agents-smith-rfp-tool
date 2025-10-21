#!/usr/bin/env python3
"""
Verifies the RFP tool is correctly set up and ready to run.
Checks dependencies, configuration, and core functionality.
"""
import sys
import os

def check_python_version():
    """Ensures Python 3.11 is being used."""
    version = sys.version_info
    if version.major != 3 or version.minor != 11:
        print(f"❌ Python {version.major}.{version.minor} detected. Need exactly 3.11")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Checks if required packages are installed."""
    required = [
        ("chainlit", "Chainlit"),
        ("gradio", "Gradio"),
        ("strands", "Strands"),
        ("docling", "Docling"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "Pydantic"),
    ]
    
    missing = []
    for module, name in required:
        try:
            __import__(module)
            print(f"✅ {name} installed")
        except ImportError:
            print(f"❌ {name} missing")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_core_files():
    """Ensures all core files exist."""
    core_files = [
        "config.py",
        "llm.py",
        "storage.py",
        "agents.py",
        "orchestrator.py",
        "document.py",
        "export.py",
        "app.py",
        "main.py",
        "start.sh",
        "docker-compose.yaml",
        "requirements.txt",
    ]
    
    missing = []
    for file in core_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} missing")
            missing.append(file)
    
    if missing:
        print(f"\n❌ Missing core files: {', '.join(missing)}")
        return False
    
    return True

def check_env_file():
    """Checks if .env file exists."""
    if os.path.exists(".env"):
        print("✅ .env file exists")
        return True
    elif os.path.exists(".env.example"):
        print("⚠️  .env file missing. Run: cp .env.example .env")
        return True
    else:
        print("❌ .env.example missing")
        return False

def check_docker():
    """Checks if Docker is available."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ Docker is running")
            return True
        else:
            print("⚠️  Docker not running. Start Docker to use local storage.")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  Docker not found. Install Docker for local storage.")
        return True

def check_imports():
    """Tests importing core modules."""
    modules = [
        "config",
        "llm",
        "storage",
        "agents",
        "orchestrator",
        "document",
        "export",
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}.py imports successfully")
        except Exception as e:
            print(f"❌ {module}.py failed to import: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n❌ Failed imports: {', '.join(failed)}")
        return False
    
    return True

def main():
    """Runs all verification checks."""
    print("🔍 Verifying RFP Tool Setup\n")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Core Files", check_core_files),
        ("Environment", check_env_file),
        ("Docker", check_docker),
        ("Imports", check_imports),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        print("-" * 50)
        results.append(check_func())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All checks passed! Ready to run: ./start.sh")
        return 0
    else:
        print("❌ Some checks failed. Fix issues above and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


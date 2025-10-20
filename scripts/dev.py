#!/usr/bin/env python3
"""
Unified CLI for AI RFP Assistant development workflow.
Provides setup, start, and health check commands.
"""

import argparse
import sys
import os
import subprocess
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_command(cmd, timeout=300):
    """Run a shell command with timeout and error handling."""
    logger.info(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, timeout=timeout, 
                              capture_output=True, text=True)
        if result.stdout:
            logger.info(result.stdout)
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds: {cmd}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {cmd}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False


def setup_command():
    """Run development environment setup."""
    logger.info("🔧 Running development setup...")
    
    # Import and run setup functions
    try:
        from setup import main as setup_main
        setup_main()
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import setup functions: {e}")
        return False
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False


def start_command():
    """Start the AI RFP Assistant services."""
    logger.info("🚀 Starting AI RFP Assistant...")
    
    # Import and run start functions
    try:
        from start import main as start_main
        start_main()
    except ImportError as e:
        logger.error(f"Failed to import start functions: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("🛑 Startup interrupted by user")
        return True
    except Exception as e:
        logger.error(f"Start failed: {e}")
        return False


def check_command():
    """Check service health."""
    logger.info("🔍 Checking service health...")
    
    try:
        from check import main as check_main
        return check_main()
    except ImportError as e:
        logger.error(f"Failed to import health check functions: {e}")
        return False
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI RFP Assistant Development CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/dev.py setup    # Setup development environment
  python scripts/dev.py start    # Start FastAPI + Chainlit
  python scripts/dev.py check    # Check service health
  python scripts/dev.py all      # Setup then start
  python scripts/dev.py          # Same as 'all'
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['setup', 'start', 'check', 'all'],
        default='all',
        help="Command to run (default: 'all')"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    os.chdir(project_root)
    
    # Execute command
    if args.command == 'setup':
        success = setup_command()
    elif args.command == 'start':
        success = start_command()
    elif args.command == 'check':
        success = check_command()
    elif args.command == 'all':
        # Run setup, then start if setup succeeded
        setup_ok = setup_command()
        success = setup_ok and start_command()
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

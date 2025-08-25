#!/usr/bin/env python3
"""
Script to run the GITTE application with detailed logging.
"""

import sys
import os
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("app_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_app():
    """Run the GITTE application."""
    try:
        logger.info("Starting GITTE application...")
        
        # Import and run the main application
        from src.ui.main import main
        main()
        
    except Exception as e:
        logger.error(f"Error running application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_app()
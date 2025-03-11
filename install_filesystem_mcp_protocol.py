#!/usr/bin/env python3
"""
Installation script for Filesystem MCP Protocol

This script installs the necessary dependencies for the Filesystem MCP Protocol
integration with Ollama Shell.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("install_filesystem_mcp_protocol")

def install_dependencies():
    """Install the required dependencies for the Filesystem MCP Protocol."""
    try:
        logger.info("Installing MCP Python SDK...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
        
        logger.info("Installing FastAPI and Uvicorn...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"])
        
        logger.info("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing dependencies: {str(e)}")
        return False

def make_executable(file_path):
    """Make a file executable."""
    try:
        os.chmod(file_path, 0o755)
        logger.info(f"Made {file_path} executable")
        return True
    except Exception as e:
        logger.error(f"Error making {file_path} executable: {str(e)}")
        return False

def main():
    """Main installation function."""
    logger.info("Starting installation of Filesystem MCP Protocol...")
    
    # Install dependencies
    if not install_dependencies():
        logger.error("Failed to install dependencies")
        return False
    
    # Make server script executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filesystem_mcp_protocol.py")
    if not make_executable(script_path):
        logger.warning(f"Failed to make {script_path} executable")
    
    logger.info("Filesystem MCP Protocol installation completed successfully!")
    logger.info("You can now use natural language commands to interact with the filesystem in Ollama Shell.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

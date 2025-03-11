#!/usr/bin/env python3
"""
Filesystem MCP Protocol Server for Ollama Shell

This module implements a Model Context Protocol (MCP) server that exposes
filesystem operations to LLMs, allowing them to interact with the filesystem
through natural language.
"""

import os
import sys
import json
import hashlib
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, AsyncIterator

# Import MCP SDK
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.types import Image
from contextlib import asynccontextmanager

# Import existing filesystem operations
from filesystem_mcp_server_simple import (
    is_path_allowed, format_timestamp, list_directory, create_directory,
    read_file, write_file, append_file, analyze_text, calculate_hash,
    find_duplicates, create_zip, extract_zip, config
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("filesystem_mcp_protocol")

# Create an MCP server
mcp = FastMCP(
    "Filesystem MCP",
    description="A Model Context Protocol server that provides filesystem operations for Ollama Shell",
    dependencies=["mcp"]
)

# Define server context
class ServerContext:
    """Server context for the Filesystem MCP Protocol server."""
    def __init__(self):
        self.config = config

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[ServerContext]:
    """Manage server lifecycle with context."""
    try:
        # Initialize on startup
        logger.info("Starting Filesystem MCP Protocol server")
        context = ServerContext()
        yield context
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Filesystem MCP Protocol server")

# Set server lifespan
mcp.lifespan = server_lifespan

# Resources
@mcp.resource("filesystem://config")
def get_config() -> str:
    """Get the server configuration."""
    return json.dumps(config, indent=2)

@mcp.resource("filesystem://allowed_paths")
def get_allowed_paths() -> str:
    """Get the list of allowed paths."""
    return json.dumps(config["allowedPaths"], indent=2)

@mcp.resource("filesystem://directory/{path}")
def get_directory_contents(path: str) -> str:
    """
    Get the contents of a directory.
    
    Args:
        path: Path to the directory
        
    Returns:
        JSON string with directory contents
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = list_directory(path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing directory: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.resource("filesystem://file/{path}")
def get_file_content(path: str, encoding: str = "utf-8") -> str:
    """
    Get the content of a file.
    
    Args:
        path: Path to the file
        encoding: File encoding (default: utf-8)
        
    Returns:
        File content or error message
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = read_file(path, encoding)
        if "content" in result:
            return result["content"]
        else:
            return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.resource("filesystem://analyze/{path}")
def get_file_analysis(path: str) -> str:
    """
    Get analysis of a text file.
    
    Args:
        path: Path to the file
        
    Returns:
        JSON string with file analysis
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = analyze_text(path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Tools
@mcp.tool()
def fs_list_directory(path: str) -> str:
    """
    List contents of a directory with metadata.
    
    Args:
        path: Path to the directory
        
    Returns:
        JSON string with directory contents
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = list_directory(path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing directory: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_create_directory(path: str) -> str:
    """
    Create a new directory.
    
    Args:
        path: Path to create
        
    Returns:
        JSON string with operation result
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = create_directory(path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_read_file(path: str, encoding: str = "utf-8") -> str:
    """
    Read content from a file.
    
    Args:
        path: Path to the file
        encoding: File encoding (default: utf-8)
        
    Returns:
        JSON string with file content
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = read_file(path, encoding)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Write content to a file.
    
    Args:
        path: Path to the file
        content: Content to write
        encoding: File encoding (default: utf-8)
        
    Returns:
        JSON string with operation result
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = write_file(path, content, encoding)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error writing file: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_append_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Append content to a file.
    
    Args:
        path: Path to the file
        content: Content to append
        encoding: File encoding (default: utf-8)
        
    Returns:
        JSON string with operation result
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = append_file(path, content, encoding)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error appending to file: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_analyze_text(path: str) -> str:
    """
    Analyze text file properties.
    
    Args:
        path: Path to the text file
        
    Returns:
        JSON string with analysis results
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = analyze_text(path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_calculate_hash(path: str, algorithm: str = "sha256") -> str:
    """
    Calculate file hash using specified algorithm.
    
    Args:
        path: Path to the file
        algorithm: Hash algorithm (default: sha256)
        
    Returns:
        JSON string with hash result
    """
    # Handle tilde expansion
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # Check if path is allowed
    if not is_path_allowed(path):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{path}' is not allowed"
        })
    
    try:
        result = calculate_hash(path, algorithm)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error calculating hash: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_find_duplicates(directory: str) -> str:
    """
    Identify duplicate files in a directory.
    
    Args:
        directory: Path to the directory
        
    Returns:
        JSON string with duplicate files
    """
    # Handle tilde expansion
    if directory.startswith('~'):
        directory = os.path.expanduser(directory)
    
    # Check if path is allowed
    if not is_path_allowed(directory):
        return json.dumps({
            "success": False,
            "error": f"Access to path '{directory}' is not allowed"
        })
    
    try:
        result = find_duplicates(directory)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error finding duplicates: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_create_zip(source_paths: List[str], output_path: str) -> str:
    """
    Create a ZIP archive.
    
    Args:
        source_paths: List of paths to include in the archive
        output_path: Path for the output ZIP file
        
    Returns:
        JSON string with operation result
    """
    # Handle tilde expansion for all paths
    expanded_source_paths = []
    for path in source_paths:
        if path.startswith('~'):
            expanded_source_paths.append(os.path.expanduser(path))
        else:
            expanded_source_paths.append(path)
    
    if output_path.startswith('~'):
        output_path = os.path.expanduser(output_path)
    
    # Check if all paths are allowed
    for path in expanded_source_paths + [output_path]:
        if not is_path_allowed(path):
            return json.dumps({
                "success": False,
                "error": f"Access to path '{path}' is not allowed"
            })
    
    try:
        result = create_zip(expanded_source_paths, output_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating ZIP: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def fs_extract_zip(zip_path: str, output_directory: str) -> str:
    """
    Extract a ZIP archive.
    
    Args:
        zip_path: Path to the ZIP file
        output_directory: Directory to extract to
        
    Returns:
        JSON string with operation result
    """
    # Handle tilde expansion
    if zip_path.startswith('~'):
        zip_path = os.path.expanduser(zip_path)
    
    if output_directory.startswith('~'):
        output_directory = os.path.expanduser(output_directory)
    
    # Check if paths are allowed
    for path in [zip_path, output_directory]:
        if not is_path_allowed(path):
            return json.dumps({
                "success": False,
                "error": f"Access to path '{path}' is not allowed"
            })
    
    try:
        result = extract_zip(zip_path, output_directory)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error extracting ZIP: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Prompts
@mcp.prompt()
def list_files_prompt(directory: str = "~") -> str:
    """Prompt for listing files in a directory."""
    return f"""
    Please list all files and directories in {directory}.
    For each item, show:
    - Name
    - Type (file or directory)
    - Size (for files)
    - Last modified date
    
    Format the output in a clear, readable way.
    """

@mcp.prompt()
def analyze_file_prompt(file_path: str) -> str:
    """Prompt for analyzing a file."""
    return f"""
    Please analyze the file at {file_path} and provide:
    - File size
    - Line count
    - Word count
    - Character count
    - File extension
    - Last modified date
    
    If it's a text file, also provide a brief summary of its content.
    """

@mcp.prompt()
def find_duplicates_prompt(directory: str = "~") -> str:
    """Prompt for finding duplicate files."""
    return f"""
    Please find all duplicate files in {directory} and its subdirectories.
    Group the duplicates by their content hash and show:
    - File paths
    - File sizes
    - Last modified dates
    
    Format the output in a clear, readable way.
    """

# Main function to run the server
def run_server(host: str = "localhost", port: int = 8765):
    """
    Run the MCP server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn
    
    logger.info(f"Starting Filesystem MCP Protocol server on {host}:{port}")
    
    # Run the server
    uvicorn.run(mcp.app, host=host, port=port)

if __name__ == "__main__":
    # Get port from command line arguments or config
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    host = "localhost"
    
    # Run the server
    run_server(host, port)

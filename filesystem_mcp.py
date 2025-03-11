#!/usr/bin/env python3
"""
Filesystem MCP Server Integration for Ollama Shell

This module integrates the Filesystem MCP Server with Ollama Shell,
allowing the LLM to perform file system operations directly.
"""

import os
import json
import requests
import logging
import time
import urllib.parse
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("filesystem_mcp")

class FilesystemMCP:
    """
    Client for the Filesystem MCP Server that provides file system operations
    for the LLM in Ollama Shell.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the Filesystem MCP client.
        
        Args:
            base_url: The base URL of the Filesystem MCP Server
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.available = self._check_server_availability()
        
        if self.available:
            logger.info(f"Filesystem MCP Server connected at {base_url}")
        else:
            logger.warning(f"Filesystem MCP Server not available at {base_url}")
            # Try to start the server if it's not available
            self._try_start_server()
    
    def _check_server_availability(self) -> bool:
        """Check if the MCP server is available."""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def _try_start_server(self) -> bool:
        """Try to start the server if it's not running."""
        try:
            server_path = os.path.expanduser("~/.ollama_shell/filesystem_mcp/start_server.sh")
            if os.path.exists(server_path):
                logger.info("Attempting to start Filesystem MCP Server...")
                import subprocess
                
                # Start the server as a background process
                subprocess.Popen(
                    ["bash", server_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Wait for the server to start
                for _ in range(5):
                    time.sleep(1)
                    if self._check_server_availability():
                        self.available = True
                        logger.info("Filesystem MCP Server started successfully")
                        return True
                
                logger.warning("Failed to start Filesystem MCP Server")
            else:
                logger.warning(f"Server start script not found at {server_path}")
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
        
        return False
    
    def _call_tool(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """
        Call an API endpoint on the MCP server.
        
        Args:
            endpoint: API endpoint to call
            method: HTTP method (GET, POST, etc.)
            **kwargs: Parameters for the API call
            
        Returns:
            Dict containing the API response
        """
        # Check if server is available, try to start it if not
        if not self.available:
            self.available = self._check_server_availability()
            if not self.available:
                self._try_start_server()
                if not self.available:
                    raise ConnectionError("Filesystem MCP Server is not available")
        
        try:
            url = f"{self.base_url}/api/{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, params=kwargs, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=kwargs, timeout=10)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=kwargs, timeout=10)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=kwargs, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error calling endpoint {endpoint}: {str(e)}")
            raise
    
    # Directory Operations
    def list_directory(self, path: str) -> Dict[str, Any]:
        """
        List contents of a directory with metadata.
        
        Args:
            path: Path to the directory
            
        Returns:
            Dict containing directory contents
        """
        # Special handling for tilde paths (home directory)
        if path.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not path.startswith('/'):
            # For user-specific paths like 'Users/christopher.bradford',
            # prepend a slash to make it absolute
            path = '/' + path
            
        # Use URL encoding for the path parameter
        url = f"{self.base_url}/api/filesystem/list?path={urllib.parse.quote(path)}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error listing directory: {str(e)}")
            raise
    
    def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Create a new directory.
        
        Args:
            path: Path to the new directory
            
        Returns:
            Dict containing operation result
        """
        # For this endpoint, path is sent as a query parameter, not in the request body
        url = f"{self.base_url}/api/filesystem/directory?path={urllib.parse.quote(path)}"
        
        try:
            response = self.session.post(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error creating directory: {str(e)}")
            raise
    
    # File Operations
    def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read content from a file.
        
        Args:
            path: Path to the file
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dict containing file content
        """
        # Special handling for tilde paths (home directory)
        if path.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not path.startswith('/'):
            # For user-specific paths, prepend a slash to make it absolute
            path = '/' + path
            
        # Use URL encoding for the path parameter
        url = f"{self.base_url}/api/filesystem/file?path={urllib.parse.quote(path)}&encoding={encoding}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error reading file: {str(e)}")
            raise
    
    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Write content to a file.
        
        Args:
            path: Path to the file
            content: Content to write
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dict containing operation result
        """
        # Special handling for tilde paths (home directory)
        if path.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not path.startswith('/'):
            # For user-specific paths, prepend a slash to make it absolute
            path = '/' + path
            
        # For write operations, we need to send the data in the request body
        data = {
            "path": path,
            "content": content,
            "encoding": encoding
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/filesystem/file", json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error writing file: {str(e)}")
            raise
    
    def append_file(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Append content to a file.
        
        Args:
            path: Path to the file
            content: Content to append
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dict containing operation result
        """
        # Special handling for tilde paths (home directory)
        if path.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not path.startswith('/'):
            # For user-specific paths, prepend a slash to make it absolute
            path = '/' + path
            
        # For append operations, we need to send the data in the request body
        data = {
            "path": path,
            "content": content,
            "encoding": encoding
        }
        
        try:
            response = self.session.post(f"{self.base_url}/api/filesystem/file/append", json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error appending to file: {str(e)}")
            raise
    
    # Analysis Operations
    def analyze_text(self, path: str) -> Dict[str, Any]:
        """
        Analyze text file properties.
        
        Args:
            path: Path to the text file
            
        Returns:
            Dict containing analysis results
        """
        # Special handling for tilde paths (home directory)
        if path.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not path.startswith('/'):
            # For user-specific paths, prepend a slash to make it absolute
            path = '/' + path
            
        # Use URL encoding for the path parameter
        url = f"{self.base_url}/api/filesystem/analyze/text?path={urllib.parse.quote(path)}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error analyzing text: {str(e)}")
            raise
    
    def calculate_hash(self, path: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """
        Calculate file hash using specified algorithm.
        
        Args:
            path: Path to the file
            algorithm: Hash algorithm (default: sha256)
            
        Returns:
            Dict containing hash result
        """
        # Special handling for tilde paths (home directory)
        if path.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not path.startswith('/'):
            # For user-specific paths, prepend a slash to make it absolute
            path = '/' + path
            
        # Use URL encoding for the path parameter
        url = f"{self.base_url}/api/filesystem/hash?path={urllib.parse.quote(path)}&algorithm={algorithm}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error calculating hash: {str(e)}")
            raise
    
    def find_duplicates(self, directory: str) -> Dict[str, Any]:
        """
        Identify duplicate files in a directory.
        
        Args:
            directory: Path to the directory
            
        Returns:
            Dict containing duplicate files
        """
        # Special handling for tilde paths (home directory)
        if directory.startswith('~'):
            # Keep the tilde as is, don't modify it
            pass
        # Handle relative paths that don't start with / or ~
        elif not directory.startswith('/'):
            # For user-specific paths, prepend a slash to make it absolute
            directory = '/' + directory
            
        # Use URL encoding for the directory parameter
        url = f"{self.base_url}/api/filesystem/duplicates?directory={urllib.parse.quote(directory)}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error finding duplicates: {str(e)}")
            raise
    
    # Compression Operations
    def create_zip(self, source_paths: List[str], output_path: str) -> Dict[str, Any]:
        """
        Create a ZIP archive.
        
        Args:
            source_paths: List of paths to include in the archive
            output_path: Path for the output ZIP file
            
        Returns:
            Dict containing operation result
        """
        return self._call_tool("filesystem/zip/create", method="POST", sourcePaths=source_paths, outputPath=output_path)
    
    def extract_zip(self, zip_path: str, output_directory: str) -> Dict[str, Any]:
        """
        Extract a ZIP archive.
        
        Args:
            zip_path: Path to the ZIP file
            output_directory: Directory to extract to
            
        Returns:
            Dict containing operation result
        """
        return self._call_tool("filesystem/zip/extract", method="POST", zipPath=zip_path, outputDirectory=output_directory)


# Singleton instance for use throughout the application
_mcp_instance = None

def get_filesystem_mcp(base_url: str = "http://localhost:8000") -> FilesystemMCP:
    """
    Get the singleton instance of the FilesystemMCP client.
    
    Args:
        base_url: The base URL of the Filesystem MCP Server
        
    Returns:
        FilesystemMCP instance
    """
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = FilesystemMCP(base_url)
    return _mcp_instance

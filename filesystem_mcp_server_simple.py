#!/usr/bin/env python3
"""
Filesystem MCP Server for Ollama Shell (Simple Version)

A simple HTTP server that provides file system operations for Ollama Shell.
"""

import os
import sys
import json
import hashlib
import zipfile
import shutil
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("filesystem_mcp")

# Default configuration
DEFAULT_CONFIG = {
    "port": 8000,
    "host": "localhost",
    "allowedPaths": [
        os.path.expanduser("~"),
        os.path.dirname(os.path.abspath(__file__))
    ],
    "restrictedPaths": [
        os.path.join(os.path.expanduser("~"), ".ssh"),
        os.path.join(os.path.expanduser("~"), ".aws"),
        os.path.join(os.path.expanduser("~"), ".config")
    ],
    "maxFileSize": 10485760,  # 10 MB
    "logLevel": "info"
}

# Load configuration
config_path = os.path.join(os.path.expanduser("~"), ".ollama_shell", "filesystem_mcp", "config.json")
try:
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
except Exception as e:
    logger.error(f"Error loading configuration: {str(e)}")
    config = DEFAULT_CONFIG

# Helper functions
def is_path_allowed(path: str) -> bool:
    """Check if a path is allowed based on configuration."""
    path = os.path.abspath(os.path.expanduser(path))
    
    # Check against allowed paths
    for allowed_path in config["allowedPaths"]:
        allowed_path = os.path.abspath(os.path.expanduser(allowed_path))
        if path.startswith(allowed_path):
            # Check against restricted paths
            for restricted_path in config["restrictedPaths"]:
                restricted_path = os.path.abspath(os.path.expanduser(restricted_path))
                if path.startswith(restricted_path):
                    return False
            return True
    
    return False

def format_timestamp(timestamp: float) -> str:
    """Format a timestamp into a readable string."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def parse_query_string(query_string: str) -> Dict[str, str]:
    """Parse query string into a dictionary."""
    if not query_string:
        return {}
    
    params = {}
    for param in query_string.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            params[key] = urllib.parse.unquote_plus(value)
        else:
            params[param] = ''
    
    return params

def list_directory(path: str) -> Dict[str, Any]:
    """List contents of a directory."""
    try:
        path = os.path.expanduser(path)
        entries = []
        
        for entry in os.scandir(path):
            entry_info = {
                "name": entry.name,
                "path": entry.path,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if not entry.is_dir() else 0,
                "modified": format_timestamp(entry.stat().st_mtime)
            }
            entries.append(entry_info)
            
        return {"success": True, "path": path, "entries": entries}
    except Exception as e:
        logger.error(f"Error listing directory: {str(e)}")
        return {"success": False, "error": str(e)}

def create_directory(path: str) -> Dict[str, Any]:
    """Create a new directory."""
    try:
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)
        return {"success": True, "path": path}
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}")
        return {"success": False, "error": str(e)}

def read_file(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Read content from a file."""
    try:
        path = os.path.expanduser(path)
        with open(path, "r", encoding=encoding) as f:
            content = f.read()
        return {"success": True, "path": path, "content": content}
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return {"success": False, "error": str(e)}

def write_file(path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Write content to a file."""
    try:
        path = os.path.expanduser(path)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return {"success": True, "path": path}
    except Exception as e:
        logger.error(f"Error writing file: {str(e)}")
        return {"success": False, "error": str(e)}

def append_file(path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Append content to a file."""
    try:
        path = os.path.expanduser(path)
        with open(path, "a", encoding=encoding) as f:
            f.write(content)
        return {"success": True, "path": path}
    except Exception as e:
        logger.error(f"Error appending to file: {str(e)}")
        return {"success": False, "error": str(e)}

def analyze_text(path: str) -> Dict[str, Any]:
    """Analyze text file properties."""
    try:
        path = os.path.expanduser(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        words = content.split()
        
        analysis = {
            "success": True,
            "path": path,
            "size_bytes": os.path.getsize(path),
            "line_count": len(lines),
            "word_count": len(words),
            "character_count": len(content),
            "file_extension": os.path.splitext(path)[1],
            "last_modified": format_timestamp(os.path.getmtime(path))
        }
        
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        return {"success": False, "error": str(e)}

def calculate_hash(path: str, algorithm: str = "sha256") -> Dict[str, Any]:
    """Calculate file hash using specified algorithm."""
    try:
        path = os.path.expanduser(path)
        
        if algorithm not in hashlib.algorithms_available:
            return {"success": False, "error": f"Unsupported hash algorithm: {algorithm}"}
        
        hash_obj = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return {
            "success": True,
            "path": path,
            "algorithm": algorithm,
            "hash": hash_obj.hexdigest()
        }
    except Exception as e:
        logger.error(f"Error calculating hash: {str(e)}")
        return {"success": False, "error": str(e)}

def find_duplicates(directory: str) -> Dict[str, Any]:
    """Identify duplicate files in a directory."""
    try:
        directory = os.path.expanduser(directory)
        
        # Dictionary to store file hashes
        hashes = {}
        duplicates = {}
        
        for root, _, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                if os.path.getsize(filepath) > config["maxFileSize"]:
                    continue
                
                # Calculate hash
                hash_obj = hashlib.sha256()
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_obj.update(chunk)
                file_hash = hash_obj.hexdigest()
                
                if file_hash in hashes:
                    if file_hash not in duplicates:
                        duplicates[file_hash] = [hashes[file_hash]]
                    duplicates[file_hash].append(filepath)
                else:
                    hashes[file_hash] = filepath
        
        return {
            "success": True,
            "directory": directory,
            "duplicates": duplicates
        }
    except Exception as e:
        logger.error(f"Error finding duplicates: {str(e)}")
        return {"success": False, "error": str(e)}

def create_zip(source_paths: List[str], output_path: str) -> Dict[str, Any]:
    """Create a ZIP archive."""
    try:
        # Expand user paths
        source_paths = [os.path.expanduser(path) for path in source_paths]
        output_path = os.path.expanduser(output_path)
        
        # Create ZIP file
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in source_paths:
                if os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(path)))
                else:
                    zipf.write(path, os.path.basename(path))
        
        return {
            "success": True,
            "output_path": output_path,
            "source_paths": source_paths
        }
    except Exception as e:
        logger.error(f"Error creating ZIP archive: {str(e)}")
        return {"success": False, "error": str(e)}

def extract_zip(zip_path: str, output_directory: str) -> Dict[str, Any]:
    """Extract a ZIP archive."""
    try:
        zip_path = os.path.expanduser(zip_path)
        output_directory = os.path.expanduser(output_directory)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        
        # Extract ZIP file
        with zipfile.ZipFile(zip_path, "r") as zipf:
            zipf.extractall(output_directory)
            extracted_files = zipf.namelist()
        
        return {
            "success": True,
            "zip_path": zip_path,
            "output_directory": output_directory,
            "extracted_files": extracted_files
        }
    except Exception as e:
        logger.error(f"Error extracting ZIP archive: {str(e)}")
        return {"success": False, "error": str(e)}

class FilesystemMCPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Filesystem MCP Server."""
    
    def _set_headers(self, status_code=200, content_type="application/json"):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _send_json_response(self, data, status_code=200):
        """Send JSON response."""
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error_response(self, error_message, status_code=400):
        """Send error response."""
        self._send_json_response({"success": False, "error": error_message}, status_code)
    
    def _parse_post_data(self):
        """Parse POST data from request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        try:
            return json.loads(post_data)
        except json.JSONDecodeError:
            return {}
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self._set_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        # Parse URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = parse_query_string(parsed_url.query)
        
        # Health check endpoint
        if path == "/api/health":
            self._send_json_response({"status": "ok"})
            return
        
        # List directory endpoint
        elif path == "/api/filesystem/list":
            if "path" not in query_params:
                self._send_error_response("Path parameter is required")
                return
            
            directory_path = query_params["path"]
            if not is_path_allowed(directory_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            result = list_directory(directory_path)
            self._send_json_response(result)
            return
        
        # Read file endpoint
        elif path == "/api/filesystem/file":
            if "path" not in query_params:
                self._send_error_response("Path parameter is required")
                return
            
            file_path = query_params["path"]
            if not is_path_allowed(file_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            encoding = query_params.get("encoding", "utf-8")
            result = read_file(file_path, encoding)
            self._send_json_response(result)
            return
        
        # Analyze text endpoint
        elif path == "/api/filesystem/analyze/text":
            if "path" not in query_params:
                self._send_error_response("Path parameter is required")
                return
            
            file_path = query_params["path"]
            if not is_path_allowed(file_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            result = analyze_text(file_path)
            self._send_json_response(result)
            return
        
        # Calculate hash endpoint
        elif path == "/api/filesystem/hash":
            if "path" not in query_params:
                self._send_error_response("Path parameter is required")
                return
            
            file_path = query_params["path"]
            if not is_path_allowed(file_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            algorithm = query_params.get("algorithm", "sha256")
            result = calculate_hash(file_path, algorithm)
            self._send_json_response(result)
            return
        
        # Find duplicates endpoint
        elif path == "/api/filesystem/duplicates":
            if "directory" not in query_params:
                self._send_error_response("Directory parameter is required")
                return
            
            directory_path = query_params["directory"]
            if not is_path_allowed(directory_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            result = find_duplicates(directory_path)
            self._send_json_response(result)
            return
        
        # Unknown endpoint
        else:
            self._send_error_response("Unknown endpoint", 404)
    
    def do_POST(self):
        """Handle POST requests."""
        # Parse URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = parse_query_string(parsed_url.query)
        
        # Create directory endpoint
        if path == "/api/filesystem/directory":
            if "path" not in query_params:
                self._send_error_response("Path parameter is required")
                return
            
            directory_path = query_params["path"]
            if not is_path_allowed(directory_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            result = create_directory(directory_path)
            self._send_json_response(result)
            return
        
        # Write file endpoint
        elif path == "/api/filesystem/file":
            post_data = self._parse_post_data()
            
            if "path" not in post_data or "content" not in post_data:
                self._send_error_response("Path and content are required")
                return
            
            file_path = post_data["path"]
            if not is_path_allowed(file_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            content = post_data["content"]
            encoding = post_data.get("encoding", "utf-8")
            result = write_file(file_path, content, encoding)
            self._send_json_response(result)
            return
        
        # Append file endpoint
        elif path == "/api/filesystem/file/append":
            post_data = self._parse_post_data()
            
            if "path" not in post_data or "content" not in post_data:
                self._send_error_response("Path and content are required")
                return
            
            file_path = post_data["path"]
            if not is_path_allowed(file_path):
                self._send_error_response("Access to this path is not allowed", 403)
                return
            
            content = post_data["content"]
            encoding = post_data.get("encoding", "utf-8")
            result = append_file(file_path, content, encoding)
            self._send_json_response(result)
            return
        
        # Create ZIP endpoint
        elif path == "/api/filesystem/zip/create":
            post_data = self._parse_post_data()
            
            if "sourcePaths" not in post_data or "outputPath" not in post_data:
                self._send_error_response("Source paths and output path are required")
                return
            
            source_paths = post_data["sourcePaths"]
            output_path = post_data["outputPath"]
            
            # Check if all paths are allowed
            for source_path in source_paths:
                if not is_path_allowed(source_path):
                    self._send_error_response(f"Access to path {source_path} is not allowed", 403)
                    return
            
            if not is_path_allowed(output_path):
                self._send_error_response(f"Access to output path {output_path} is not allowed", 403)
                return
            
            result = create_zip(source_paths, output_path)
            self._send_json_response(result)
            return
        
        # Extract ZIP endpoint
        elif path == "/api/filesystem/zip/extract":
            post_data = self._parse_post_data()
            
            if "zipPath" not in post_data or "outputDirectory" not in post_data:
                self._send_error_response("ZIP path and output directory are required")
                return
            
            zip_path = post_data["zipPath"]
            output_directory = post_data["outputDirectory"]
            
            if not is_path_allowed(zip_path):
                self._send_error_response("Access to ZIP path is not allowed", 403)
                return
            
            if not is_path_allowed(output_directory):
                self._send_error_response("Access to output directory is not allowed", 403)
                return
            
            result = extract_zip(zip_path, output_directory)
            self._send_json_response(result)
            return
        
        # Unknown endpoint
        else:
            self._send_error_response("Unknown endpoint", 404)

def run_server(host="localhost", port=8000):
    """Run the HTTP server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, FilesystemMCPHandler)
    logger.info(f"Starting Filesystem MCP Server on {host}:{port}")
    print(f"Starting Filesystem MCP Server on {host}:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Get port from command line arguments or config
    port = int(sys.argv[1]) if len(sys.argv) > 1 else config["port"]
    host = config["host"]
    
    # Run server
    run_server(host, port)

#!/usr/bin/env python3
"""
Filesystem MCP Server for Ollama Shell (Flask Version)

A simple Flask server that provides file system operations for Ollama Shell.
"""

import os
import sys
import json
import hashlib
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from flask import Flask, request, jsonify

# Create Flask app
app = Flask(__name__)

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
    print(f"Error loading configuration: {str(e)}")
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

# API endpoints
@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

@app.route("/api/filesystem/list", methods=["GET"])
def list_directory():
    """List contents of a directory."""
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path parameter is required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
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
            
        return jsonify({"path": path, "entries": entries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/directory", methods=["POST"])
def create_directory():
    """Create a new directory."""
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path parameter is required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
    try:
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/file", methods=["GET"])
def read_file():
    """Read content from a file."""
    path = request.args.get("path")
    encoding = request.args.get("encoding", "utf-8")
    
    if not path:
        return jsonify({"error": "Path parameter is required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
    try:
        path = os.path.expanduser(path)
        with open(path, "r", encoding=encoding) as f:
            content = f.read()
        return jsonify({"success": True, "path": path, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/file", methods=["POST"])
def write_file():
    """Write content to a file."""
    data = request.get_json()
    path = data.get("path")
    content = data.get("content")
    encoding = data.get("encoding", "utf-8")
    
    if not path or content is None:
        return jsonify({"error": "Path and content are required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
    try:
        path = os.path.expanduser(path)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/file/append", methods=["POST"])
def append_file():
    """Append content to a file."""
    data = request.get_json()
    path = data.get("path")
    content = data.get("content")
    encoding = data.get("encoding", "utf-8")
    
    if not path or content is None:
        return jsonify({"error": "Path and content are required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
    try:
        path = os.path.expanduser(path)
        with open(path, "a", encoding=encoding) as f:
            f.write(content)
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/analyze/text", methods=["GET"])
def analyze_text():
    """Analyze text file properties."""
    path = request.args.get("path")
    
    if not path:
        return jsonify({"error": "Path parameter is required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
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
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/hash", methods=["GET"])
def calculate_hash():
    """Calculate file hash using specified algorithm."""
    path = request.args.get("path")
    algorithm = request.args.get("algorithm", "sha256")
    
    if not path:
        return jsonify({"error": "Path parameter is required"}), 400
    
    if not is_path_allowed(path):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
    try:
        path = os.path.expanduser(path)
        
        if algorithm not in hashlib.algorithms_available:
            return jsonify({"error": f"Unsupported hash algorithm: {algorithm}"}), 400
        
        hash_obj = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return jsonify({
            "success": True,
            "path": path,
            "algorithm": algorithm,
            "hash": hash_obj.hexdigest()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/duplicates", methods=["GET"])
def find_duplicates():
    """Identify duplicate files in a directory."""
    directory = request.args.get("directory")
    
    if not directory:
        return jsonify({"error": "Directory parameter is required"}), 400
    
    if not is_path_allowed(directory):
        return jsonify({"error": "Access to this path is not allowed"}), 403
    
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
        
        return jsonify({
            "success": True,
            "directory": directory,
            "duplicates": duplicates
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/zip/create", methods=["POST"])
def create_zip():
    """Create a ZIP archive."""
    data = request.get_json()
    source_paths = data.get("sourcePaths")
    output_path = data.get("outputPath")
    
    if not source_paths or not output_path:
        return jsonify({"error": "Source paths and output path are required"}), 400
    
    # Check if all source paths are allowed
    for path in source_paths:
        if not is_path_allowed(path):
            return jsonify({"error": f"Access to path {path} is not allowed"}), 403
    
    if not is_path_allowed(output_path):
        return jsonify({"error": f"Access to output path {output_path} is not allowed"}), 403
    
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
        
        return jsonify({
            "success": True,
            "output_path": output_path,
            "source_paths": source_paths
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/filesystem/zip/extract", methods=["POST"])
def extract_zip():
    """Extract a ZIP archive."""
    data = request.get_json()
    zip_path = data.get("zipPath")
    output_directory = data.get("outputDirectory")
    
    if not zip_path or not output_directory:
        return jsonify({"error": "ZIP path and output directory are required"}), 400
    
    if not is_path_allowed(zip_path):
        return jsonify({"error": "Access to ZIP path is not allowed"}), 403
    
    if not is_path_allowed(output_directory):
        return jsonify({"error": "Access to output directory is not allowed"}), 403
    
    try:
        zip_path = os.path.expanduser(zip_path)
        output_directory = os.path.expanduser(output_directory)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        
        # Extract ZIP file
        with zipfile.ZipFile(zip_path, "r") as zipf:
            zipf.extractall(output_directory)
            extracted_files = zipf.namelist()
        
        return jsonify({
            "success": True,
            "zip_path": zip_path,
            "output_directory": output_directory,
            "extracted_files": extracted_files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Get port from command line arguments or config
    port = int(sys.argv[1]) if len(sys.argv) > 1 else config["port"]
    host = config["host"]
    
    print(f"Starting Filesystem MCP Server on {host}:{port}")
    app.run(host=host, port=port, debug=False)

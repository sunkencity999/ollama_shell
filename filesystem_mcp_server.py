#!/usr/bin/env python3
"""
Filesystem MCP Server for Ollama Shell

A simple FastAPI server that provides file system operations for Ollama Shell.
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
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Create FastAPI app
app = FastAPI(title="Filesystem MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/filesystem/list")
def list_directory(path: str = Query(..., description="Path to list")):
    """List contents of a directory."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
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
            
        return {"path": path, "entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filesystem/directory")
def create_directory(path: str = Query(..., description="Path to create")):
    """Create a new directory."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/filesystem/file")
def read_file(path: str = Query(..., description="Path to read"), 
              encoding: str = Query("utf-8", description="File encoding")):
    """Read content from a file."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = os.path.expanduser(path)
        with open(path, "r", encoding=encoding) as f:
            content = f.read()
        return {"success": True, "path": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filesystem/file")
def write_file(path: str, content: str, encoding: str = "utf-8"):
    """Write content to a file."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = os.path.expanduser(path)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filesystem/file/append")
def append_file(path: str, content: str, encoding: str = "utf-8"):
    """Append content to a file."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = os.path.expanduser(path)
        with open(path, "a", encoding=encoding) as f:
            f.write(content)
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/filesystem/analyze/text")
def analyze_text(path: str = Query(..., description="Path to analyze")):
    """Analyze text file properties."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/filesystem/hash")
def calculate_hash(path: str = Query(..., description="Path to hash"), 
                   algorithm: str = Query("sha256", description="Hash algorithm")):
    """Calculate file hash using specified algorithm."""
    if not is_path_allowed(path):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
    try:
        path = os.path.expanduser(path)
        
        if algorithm not in hashlib.algorithms_available:
            raise HTTPException(status_code=400, detail=f"Unsupported hash algorithm: {algorithm}")
        
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/filesystem/duplicates")
def find_duplicates(directory: str = Query(..., description="Directory to search")):
    """Identify duplicate files in a directory."""
    if not is_path_allowed(directory):
        raise HTTPException(status_code=403, detail="Access to this path is not allowed")
    
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filesystem/zip/create")
def create_zip(sourcePaths: List[str], outputPath: str):
    """Create a ZIP archive."""
    # Check if all source paths are allowed
    for path in sourcePaths:
        if not is_path_allowed(path):
            raise HTTPException(status_code=403, detail=f"Access to path {path} is not allowed")
    
    if not is_path_allowed(outputPath):
        raise HTTPException(status_code=403, detail=f"Access to output path {outputPath} is not allowed")
    
    try:
        # Expand user paths
        source_paths = [os.path.expanduser(path) for path in sourcePaths]
        output_path = os.path.expanduser(outputPath)
        
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filesystem/zip/extract")
def extract_zip(zipPath: str, outputDirectory: str):
    """Extract a ZIP archive."""
    if not is_path_allowed(zipPath):
        raise HTTPException(status_code=403, detail="Access to ZIP path is not allowed")
    
    if not is_path_allowed(outputDirectory):
        raise HTTPException(status_code=403, detail="Access to output directory is not allowed")
    
    try:
        zip_path = os.path.expanduser(zipPath)
        output_directory = os.path.expanduser(outputDirectory)
        
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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Get port from command line arguments or config
    port = int(sys.argv[1]) if len(sys.argv) > 1 else config["port"]
    host = config["host"]
    
    print(f"Starting Filesystem MCP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

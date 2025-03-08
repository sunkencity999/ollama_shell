#!/usr/bin/env python3
"""
Create necessary directories for Ollama Shell
This script creates the "Created Files" directory structure for storing user data
"""

import os
import sys

def create_directories():
    """Create necessary directories for Ollama Shell"""
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create the Created Files directory and its subdirectories
    created_files_dir = os.path.join(project_root, "Created Files")
    os.makedirs(created_files_dir, exist_ok=True)
    
    # Create subdirectories for different types of user data
    subdirs = [
        os.path.join(created_files_dir, "jobs"),
        os.path.join(created_files_dir, "datasets"),
        os.path.join(created_files_dir, "models"),
        os.path.join(created_files_dir, "exports")
    ]
    
    for subdir in subdirs:
        os.makedirs(subdir, exist_ok=True)
        
    print(f"✅ Created user data directories in {created_files_dir}")
    return True

if __name__ == "__main__":
    print("🚀 Creating directories for Ollama Shell...")
    success = create_directories()
    if success:
        print("🎉 Directory setup complete!")
    else:
        print("❌ Failed to create directories")
        sys.exit(1)

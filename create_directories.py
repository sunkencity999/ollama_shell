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
        os.path.join(created_files_dir, "exports"),
        os.path.join(created_files_dir, "config")
    ]
    
    for subdir in subdirs:
        os.makedirs(subdir, exist_ok=True)
    
    # Create template configuration files
    create_template_configs(created_files_dir)
        
    print(f"✅ Created user data directories in {created_files_dir}")
    return True

def create_template_configs(created_files_dir):
    """Create template configuration files"""
    # Create template Confluence configuration file
    config_dir = os.path.join(created_files_dir, "config")
    confluence_config_template = os.path.join(config_dir, "confluence_config_template.env")
    
    # Only create the template if it doesn't exist
    if not os.path.exists(confluence_config_template):
        with open(confluence_config_template, "w") as f:
            f.write("# Confluence Configuration\n")
            f.write("# Copy this file to 'confluence_config.env' and update with your values\n\n")
            f.write("# Confluence Server URL (e.g., https://wiki.example.com)\n")
            f.write("CONFLUENCE_URL=\n\n")
            f.write("# Your username/email for Confluence\n")
            f.write("CONFLUENCE_EMAIL=\n\n")
            f.write("# Your Personal Access Token (PAT) or API token\n")
            f.write("CONFLUENCE_API_TOKEN=\n\n")
            f.write("# Authentication method (basic, bearer, or pat)\n")
            f.write("CONFLUENCE_AUTH_METHOD=pat\n\n")
            f.write("# Is this a Confluence Cloud instance? (true/false)\n")
            f.write("CONFLUENCE_IS_CLOUD=false\n")
        
        print(f"✅ Created template Confluence configuration file: {confluence_config_template}")

if __name__ == "__main__":
    print("🚀 Creating directories for Ollama Shell...")
    success = create_directories()
    if success:
        print("🎉 Directory setup complete!")
    else:
        print("❌ Failed to create directories")
        sys.exit(1)

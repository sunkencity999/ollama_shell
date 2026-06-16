#!/usr/bin/env python3
"""
Filesystem MCP Server Installation Script (Simple Version)

This script installs and configures the Simple HTTP-based Filesystem MCP Server for Ollama Shell.
"""

import os
import sys
import json
import shutil
import subprocess
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

# Constants
INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".ollama_shell", "filesystem_mcp")
CONFIG_FILE = os.path.join(INSTALL_DIR, "config.json")

def check_prerequisites():
    """Check if all prerequisites are installed."""
    console.print("[bold]Checking prerequisites...[/bold]")
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"Python version: {python_version}")
    
    return True

def create_install_directory():
    """Create the installation directory."""
    console.print("\n[bold]Creating installation directory...[/bold]")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    console.print(f"Installation directory created: {INSTALL_DIR}")
    return True

def copy_server_file():
    """Copy the server file to the installation directory."""
    console.print("\n[bold]Copying server file...[/bold]")
    server_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filesystem_mcp_server_simple.py")
    server_dest = os.path.join(INSTALL_DIR, "filesystem_mcp_server.py")
    
    try:
        shutil.copy2(server_source, server_dest)
        os.chmod(server_dest, 0o755)  # Make executable
        console.print(f"Server file copied to: {server_dest}")
        return True
    except Exception as e:
        console.print(f"[red]Error copying server file: {str(e)}[/red]")
        return False

def configure_server():
    """Configure the server."""
    console.print("\n[bold]Configuring server...[/bold]")
    
    # Default configuration
    config = {
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
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        console.print(f"Configuration file created: {CONFIG_FILE}")
        return True
    except Exception as e:
        console.print(f"[red]Error creating configuration file: {str(e)}[/red]")
        return False

def create_start_script():
    """Create a script to start the server."""
    console.print("\n[bold]Creating start script...[/bold]")
    
    start_script_path = os.path.join(INSTALL_DIR, "start_server.sh")
    
    script_content = f"""#!/bin/bash
cd {INSTALL_DIR}
python filesystem_mcp_server.py
"""
    
    try:
        with open(start_script_path, "w") as f:
            f.write(script_content)
        os.chmod(start_script_path, 0o755)  # Make executable
        console.print(f"Start script created: {start_script_path}")
        return True
    except Exception as e:
        console.print(f"[red]Error creating start script: {str(e)}[/red]")
        return False

def start_server():
    """Start the server."""
    console.print("\n[bold]Starting server...[/bold]")
    
    server_path = os.path.join(INSTALL_DIR, "filesystem_mcp_server.py")
    
    try:
        # Start the server as a background process
        process = subprocess.Popen(
            ["python", server_path],
            cwd=INSTALL_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for the server to start
        time.sleep(2)
        
        # Check if the server is still running
        if process.poll() is not None:
            # Server exited
            stdout, stderr = process.communicate()
            console.print(f"[red]Server exited with code {process.returncode}[/red]")
            console.print(f"[red]Output: {stdout}[/red]")
            console.print(f"[red]Error: {stderr}[/red]")
            return False
        
        # Try to connect to the server
        try:
            import urllib.request
            response = urllib.request.urlopen("http://localhost:8000/api/health")
            if response.getcode() == 200:
                console.print("[green]Server started successfully![/green]")
                console.print("Server is running at: http://localhost:8000")
                return True
        except Exception as e:
            console.print(f"[yellow]Could not connect to server: {str(e)}[/yellow]")
            console.print("[yellow]Server may still be starting up...[/yellow]")
        
        console.print("[yellow]Server process is running, but health check could not be completed.[/yellow]")
        console.print("You can manually check if the server is running at: http://localhost:8000/api/health")
        return True
    except Exception as e:
        console.print(f"[red]Error starting server: {str(e)}[/red]")
        return False

def main():
    """Main function."""
    console.print(Panel.fit("Filesystem MCP Server Setup", title_align="center"))
    
    # Check prerequisites
    if not check_prerequisites():
        return
    
    # Create installation directory
    if not create_install_directory():
        return
    
    # Copy server file
    if not copy_server_file():
        return
    
    # Configure server
    if not configure_server():
        return
    
    # Create start script
    if not create_start_script():
        return
    
    # Start server
    if not start_server():
        return
    
    console.print("\n[green]Filesystem MCP Server setup completed successfully![/green]")
    console.print("You can now use the filesystem commands in Ollama Shell.")
    console.print("To manually start the server, run: bash ~/.ollama_shell/filesystem_mcp/start_server.sh")

if __name__ == "__main__":
    main()

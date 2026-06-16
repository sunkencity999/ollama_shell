#!/usr/bin/env python3
"""
Filesystem MCP Server Installation Script (Flask Version)

This script installs and configures the Flask-based Filesystem MCP Server for Ollama Shell.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

# Constants
INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".ollama_shell", "filesystem_mcp")
CONFIG_FILE = os.path.join(INSTALL_DIR, "config.json")
REQUIREMENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements_mcp_flask.txt")

def check_prerequisites():
    """Check if all prerequisites are installed."""
    console.print("[bold]Checking prerequisites...[/bold]")
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"Python version: {python_version}")
    
    # Check pip
    try:
        subprocess.run(["pip", "--version"], check=True, capture_output=True)
        console.print("pip: [green]Installed[/green]")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("pip: [red]Not installed[/red]")
        console.print("[red]Please install pip before continuing.[/red]")
        return False
    
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
    server_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filesystem_mcp_server_flask.py")
    server_dest = os.path.join(INSTALL_DIR, "filesystem_mcp_server.py")
    
    try:
        shutil.copy2(server_source, server_dest)
        os.chmod(server_dest, 0o755)  # Make executable
        console.print(f"Server file copied to: {server_dest}")
        return True
    except Exception as e:
        console.print(f"[red]Error copying server file: {str(e)}[/red]")
        return False

def create_requirements_file():
    """Create the requirements file for the server."""
    console.print("\n[bold]Creating requirements file...[/bold]")
    
    requirements = [
        "flask==2.2.3"
    ]
    
    try:
        with open(REQUIREMENTS_FILE, "w") as f:
            f.write("\n".join(requirements))
        console.print(f"Requirements file created: {REQUIREMENTS_FILE}")
        return True
    except Exception as e:
        console.print(f"[red]Error creating requirements file: {str(e)}[/red]")
        return False

def install_dependencies():
    """Install Python dependencies."""
    console.print("\n[bold]Installing dependencies...[/bold]")
    
    try:
        subprocess.run(["pip", "install", "-r", REQUIREMENTS_FILE], check=True)
        console.print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
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
        
        # Check if the server started successfully
        for _ in range(5):  # Wait for up to 5 seconds
            if process.poll() is not None:
                # Server exited
                stdout, stderr = process.communicate()
                console.print(f"[red]Server exited with code {process.returncode}[/red]")
                console.print(f"[red]Output: {stdout}[/red]")
                console.print(f"[red]Error: {stderr}[/red]")
                return False
            
            # Try to connect to the server
            try:
                import requests
                response = requests.get("http://localhost:8000/api/health")
                if response.status_code == 200:
                    console.print("[green]Server started successfully![/green]")
                    console.print("Server is running at: http://localhost:8000")
                    return True
            except:
                pass
            
            import time
            time.sleep(1)
        
        console.print("[yellow]Server may be starting, but health check timed out.[/yellow]")
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
    
    # Create requirements file
    if not create_requirements_file():
        return
    
    # Install dependencies
    if not install_dependencies():
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

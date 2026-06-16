#!/usr/bin/env python3
"""
Install and Setup Script for Filesystem MCP Server

This script installs and configures the Filesystem MCP Server for Ollama Shell.
"""

import os
import sys
import json
import subprocess
import platform
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# Configuration
MCP_REPO_URL = "https://github.com/bsmi021/mcp-filesystem-server.git"
MCP_INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".ollama_shell", "filesystem_mcp")
MCP_CONFIG_FILE = os.path.join(MCP_INSTALL_DIR, "config.json")
MCP_PORT = 8000

def check_prerequisites():
    """Check if all prerequisites are installed."""
    console.print("[bold cyan]Checking prerequisites...[/bold cyan]")
    
    # Check Python version
    python_version = platform.python_version()
    console.print(f"Python version: {python_version}")
    if tuple(map(int, python_version.split('.'))) < (3, 8):
        console.print("[red]Error: Python 3.8 or higher is required.[/red]")
        return False
    
    # Check Git
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        console.print("Git: Installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print("[red]Error: Git is not installed or not in PATH.[/red]")
        return False
    
    # Check pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        console.print("pip: Installed")
    except subprocess.SubprocessError:
        console.print("[red]Error: pip is not installed or not working properly.[/red]")
        return False
    
    return True

def clone_repository():
    """Clone the Filesystem MCP Server repository."""
    console.print("\n[bold cyan]Cloning Filesystem MCP Server repository...[/bold cyan]")
    
    # Create installation directory if it doesn't exist
    os.makedirs(MCP_INSTALL_DIR, exist_ok=True)
    
    # Check if repository already exists
    if os.path.exists(os.path.join(MCP_INSTALL_DIR, ".git")):
        console.print("Repository already exists. Pulling latest changes...")
        try:
            subprocess.run(["git", "pull"], cwd=MCP_INSTALL_DIR, check=True)
            console.print("[green]Repository updated successfully.[/green]")
        except subprocess.SubprocessError as e:
            console.print(f"[red]Error updating repository: {str(e)}[/red]")
            return False
    else:
        # Clone the repository
        try:
            subprocess.run(["git", "clone", MCP_REPO_URL, MCP_INSTALL_DIR], check=True)
            console.print("[green]Repository cloned successfully.[/green]")
        except subprocess.SubprocessError as e:
            console.print(f"[red]Error cloning repository: {str(e)}[/red]")
            return False
    
    return True

def install_dependencies():
    """Install the required dependencies."""
    console.print("\n[bold cyan]Installing dependencies...[/bold cyan]")
    
    # Check if npm is installed
    try:
        subprocess.run(["npm", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        console.print("npm: Installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print("[red]Error: npm is not installed or not in PATH.[/red]")
        console.print("[yellow]Please install Node.js and npm before continuing.[/yellow]")
        return False
    
    # Install npm dependencies
    try:
        console.print("Installing npm dependencies...")
        subprocess.run(["npm", "install"], cwd=MCP_INSTALL_DIR, check=True)
        console.print("[green]npm dependencies installed successfully.[/green]")
    except subprocess.SubprocessError as e:
        console.print(f"[red]Error installing npm dependencies: {str(e)}[/red]")
        return False
    
    # Install Python dependencies for the client
    try:
        console.print("Installing Python client dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
        console.print("[green]Python client dependencies installed successfully.[/green]")
    except subprocess.SubprocessError as e:
        console.print(f"[red]Error installing Python client dependencies: {str(e)}[/red]")
        return False
    
    return True

def configure_server():
    """Configure the Filesystem MCP Server."""
    console.print("\n[bold cyan]Configuring Filesystem MCP Server...[/bold cyan]")
    
    # Create the Created Files directory if it doesn't exist
    created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Created Files")
    os.makedirs(created_files_dir, exist_ok=True)
    
    # Create default configuration
    config = {
        "port": MCP_PORT,
        "host": "localhost",
        "allowedPaths": [
            os.path.expanduser("~"),
            os.path.dirname(os.path.abspath(__file__)),
            created_files_dir
        ],
        "restrictedPaths": [
            os.path.join(os.path.expanduser("~"), ".ssh"),
            os.path.join(os.path.expanduser("~"), ".aws"),
            os.path.join(os.path.expanduser("~"), ".config")
        ],
        "maxFileSize": 10485760,  # 10 MB
        "logLevel": "info"
    }
    
    # Write configuration to file
    try:
        # Create a directory for the config if it doesn't exist
        os.makedirs(os.path.dirname(MCP_CONFIG_FILE), exist_ok=True)
        
        with open(MCP_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        console.print(f"[green]Configuration saved to {MCP_CONFIG_FILE}[/green]")
        
        # Also create a client config file for the Python client
        client_config = {
            "mcp_url": f"http://localhost:{MCP_PORT}",
            "api_key": ""
        }
        
        client_config_file = os.path.join(os.path.dirname(MCP_CONFIG_FILE), "client_config.json")
        with open(client_config_file, 'w') as f:
            json.dump(client_config, f, indent=4)
        console.print(f"[green]Client configuration saved to {client_config_file}[/green]")
        
        return True
    except Exception as e:
        console.print(f"[red]Error saving configuration: {str(e)}[/red]")
        return False
    
    return True

def start_server():
    """Build and start the Filesystem MCP Server."""
    console.print("\n[bold cyan]Building and starting Filesystem MCP Server...[/bold cyan]")
    
    try:
        # Check if server is already running
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('localhost', MCP_PORT))
        s.close()
        
        if result == 0:
            console.print(f"[yellow]Filesystem MCP Server is already running on port {MCP_PORT}.[/yellow]")
            return True
        
        # Build the server
        console.print("Building the server...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=MCP_INSTALL_DIR, check=True)
            console.print("[green]Server built successfully.[/green]")
        except subprocess.SubprocessError as e:
            console.print(f"[red]Error building server: {str(e)}[/red]")
            return False
        
        # Start the server
        console.print("Starting the server...")
        
        # Copy the config file to the right location if needed
        config_dir = os.path.join(MCP_INSTALL_DIR, "build")
        os.makedirs(config_dir, exist_ok=True)
        
        # Use subprocess.Popen to start the server in the background
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=MCP_INSTALL_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True  # Detach the process
        )
        
        # Wait a moment to check if the server started successfully
        import time
        time.sleep(5)
        
        # Check if the process is still running and if the server is responding
        if process.poll() is None:
            # Try to connect to the server
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex(('localhost', MCP_PORT))
            s.close()
            
            if result == 0:
                console.print(f"[green]Filesystem MCP Server started successfully on port {MCP_PORT}.[/green]")
                
                # Display instructions
                instructions = f"""
# Filesystem MCP Server

The Filesystem MCP Server is now running on [bold]http://localhost:{MCP_PORT}[/bold].

## Using the Filesystem Integration in Ollama Shell

- Use the `/fs` command in Ollama Shell to access filesystem operations
- Type `/fs help` to see available commands
- Or select "Filesystem" from the main menu

## Server Management

- The server will continue running in the background
- To stop the server, use the task manager or `kill` command
- To restart the server, run this script again
"""
                console.print(Panel(Markdown(instructions), title="Instructions", border_style="green"))
                
                return True
            else:
                stdout, stderr = process.communicate()
                console.print(f"[red]Server started but is not responding on port {MCP_PORT}.[/red]")
                if stderr:
                    console.print(f"[red]Error output:[/red]\n{stderr}")
                return False
        else:
            stdout, stderr = process.communicate()
            console.print(f"[red]Error starting server:[/red]")
            if stderr:
                console.print(f"[red]Error output:[/red]\n{stderr}")
            return False
            
    except Exception as e:
        console.print(f"[red]Error starting server: {str(e)}[/red]")
        return False

def main():
    """Main function to install and start the Filesystem MCP Server."""
    console.print(Panel.fit("Filesystem MCP Server Setup", border_style="cyan"))
    
    if not check_prerequisites():
        console.print("[red]Prerequisites check failed. Please install the required software and try again.[/red]")
        return
    
    if not clone_repository():
        console.print("[red]Failed to clone repository. Setup aborted.[/red]")
        return
    
    if not install_dependencies():
        console.print("[red]Failed to install dependencies. Setup aborted.[/red]")
        return
    
    if not configure_server():
        console.print("[red]Failed to configure server. Setup aborted.[/red]")
        return
    
    if not start_server():
        console.print("[red]Failed to start server. Setup aborted.[/red]")
        return
    
    console.print("\n[bold green]Setup completed successfully![/bold green]")

if __name__ == "__main__":
    main()

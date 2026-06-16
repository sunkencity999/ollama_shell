#!/usr/bin/env python3
"""
Test script for the /fsnl command handler in Ollama Shell.

This script directly tests the command handler for the /fsnl command
without running the full Ollama Shell application.
"""

import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import the necessary modules
from ollama_shell_filesystem_mcp import get_ollama_shell_filesystem_mcp

console = Console()

def test_fsnl_command_handler():
    """Test the /fsnl command handler."""
    console.print(Panel.fit("Testing /fsnl Command Handler", title_align="center"))
    
    # Get the Ollama Shell Filesystem MCP integration
    integration = get_ollama_shell_filesystem_mcp()
    
    # Get the available models from Ollama
    try:
        import requests
        import json
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                # Use the first available model
                model_name = models[0].get("name")
                console.print(f"[green]Using available model:[/green] {model_name}")
            else:
                model_name = "llama3.2"  # Default fallback
                console.print(f"[yellow]No models found, using default:[/yellow] {model_name}")
        else:
            model_name = "llama3.2"  # Default fallback
            console.print(f"[yellow]Error getting models, using default:[/yellow] {model_name}")
    except Exception as e:
        model_name = "llama3.2"  # Default fallback
        console.print(f"[yellow]Exception getting models, using default:[/yellow] {model_name}")
        console.print(f"[dim]{str(e)}[/dim]")
    
    if not integration.available:
        console.print("[red]✗[/red] Ollama Shell Filesystem MCP integration not available")
        return False
    
    console.print("[green]✓[/green] Ollama Shell Filesystem MCP integration available")
    
    # Test commands
    test_commands = [
        "List the files in my home directory",
        "Create a new directory called 'test_fsnl' in my home directory",
        "Write a file called 'hello.txt' in the 'test_fsnl' directory with the content 'Hello, world!'"
    ]
    
    for command in test_commands:
        console.print(Panel.fit(f"Testing command: {command}", title_align="center"))
        
        # Handle the command with the detected model
        response = integration.handle_command(command, model_name)
        
        # Display the response
        console.print(Markdown(response))
        
        # Add a small delay between commands
        time.sleep(1)
    
    return True

if __name__ == "__main__":
    console.print("[bold]Testing /fsnl Command Handler[/bold]")
    
    if test_fsnl_command_handler():
        console.print("[green]All tests completed successfully.[/green]")
    else:
        console.print("[red]Tests failed.[/red]")

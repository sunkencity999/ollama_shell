#!/usr/bin/env python3
"""
Test script for the natural language filesystem command functionality.

This script tests the /fsnl command functionality to ensure it works correctly
with the Filesystem MCP Protocol integration.
"""

import os
import sys
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import the filesystem MCP integration
from filesystem_mcp_integration import get_filesystem_mcp_integration
from ollama_shell_filesystem_mcp import get_ollama_shell_filesystem_mcp, handle_filesystem_nl_command

console = Console()

def test_filesystem_mcp_integration():
    """Test the Filesystem MCP Protocol integration."""
    console.print(Panel.fit("Testing Filesystem MCP Protocol Integration", title_align="center"))
    
    # Get the integration instance
    integration = get_filesystem_mcp_integration()
    
    if integration.available:
        console.print("[green]✓[/green] Filesystem MCP Protocol integration available")
        return True
    else:
        console.print("[red]✗[/red] Filesystem MCP Protocol integration not available")
        return False

def test_ollama_shell_filesystem_mcp():
    """Test the Ollama Shell Filesystem MCP integration."""
    console.print(Panel.fit("Testing Ollama Shell Filesystem MCP Integration", title_align="center"))
    
    # Get the integration instance
    integration = get_ollama_shell_filesystem_mcp()
    
    if integration.available:
        console.print("[green]✓[/green] Ollama Shell Filesystem MCP integration available")
        return True
    else:
        console.print("[red]✗[/red] Ollama Shell Filesystem MCP integration not available")
        return False

def test_natural_language_command(command, model="llama3.2"):
    """Test a natural language filesystem command."""
    console.print(Panel.fit(f"Testing Natural Language Command: '{command}'", title_align="center"))
    
    # Show a spinner while processing
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Processing natural language command...[/cyan]"),
        transient=True
    ) as progress:
        progress.add_task("Processing", total=None)
        
        # Handle natural language filesystem command
        response = handle_filesystem_nl_command(command, model)
    
    # Display the response as markdown
    console.print(Markdown(response))
    
    return True

def main():
    """Main test function."""
    console.print("[bold]Testing Natural Language Filesystem Command Functionality[/bold]")
    
    # Test the Filesystem MCP Protocol integration
    if not test_filesystem_mcp_integration():
        console.print("[red]Filesystem MCP Protocol integration test failed. Exiting.[/red]")
        return
    
    # Test the Ollama Shell Filesystem MCP integration
    if not test_ollama_shell_filesystem_mcp():
        console.print("[red]Ollama Shell Filesystem MCP integration test failed. Exiting.[/red]")
        return
    
    # Test natural language commands
    test_commands = [
        "List the files in my home directory",
        "Create a new directory called 'test_fsnl' in my home directory",
        "Write a file called 'hello.txt' in the 'test_fsnl' directory with the content 'Hello, world!'"
    ]
    
    for command in test_commands:
        test_natural_language_command(command)
        time.sleep(1)  # Add a small delay between commands
    
    console.print("[green]All tests completed.[/green]")

if __name__ == "__main__":
    main()

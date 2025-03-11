#!/usr/bin/env python3
"""
Test script for the Filesystem Integration in Ollama Shell.

This script simulates the chat interface's interaction with the filesystem
integration to ensure that commands are properly processed and responses
are correctly formatted.
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel

# Import the filesystem integration
from filesystem_integration import handle_fs_command, get_filesystem_integration

console = Console()

def test_filesystem_commands():
    """Test various filesystem commands through the integration layer."""
    console.print(Panel.fit("Testing Filesystem Integration", title_align="center"))
    
    # Get the filesystem integration instance
    fs = get_filesystem_integration()
    
    if not fs.available:
        console.print("[red]⚠️ Filesystem MCP Server is not available. Starting the server...[/red]")
        # The get_filesystem_integration function should have attempted to start the server
        fs = get_filesystem_integration()
        if not fs.available:
            console.print("[red]⚠️ Failed to start Filesystem MCP Server. Tests cannot continue.[/red]")
            return False
    
    console.print("[green]✓[/green] Filesystem MCP Server is available")
    
    # Test directory for our tests
    test_dir = os.path.expanduser("~/ollama_shell_test_integration")
    
    # List of commands to test
    commands = [
        # Help command
        ["help"],
        
        # Directory operations
        ["mkdir", test_dir],
        ["ls", os.path.dirname(test_dir)],
        
        # File operations
        ["write", os.path.join(test_dir, "test.txt"), "This is a test file created by the integration test."],
        ["read", os.path.join(test_dir, "test.txt")],
        ["append", os.path.join(test_dir, "test.txt"), "This line was appended to the file."],
        ["read", os.path.join(test_dir, "test.txt")],
        
        # Analysis operations
        ["analyze", os.path.join(test_dir, "test.txt")],
        ["hash", os.path.join(test_dir, "test.txt")],
        
        # Status command
        ["status"]
    ]
    
    # Execute each command and display the result
    for cmd in commands:
        cmd_str = " ".join(cmd)
        console.print(f"\n[bold cyan]Command:[/bold cyan] /fs {cmd_str}")
        
        try:
            result = handle_fs_command(cmd)
            console.print(f"[bold green]Result:[/bold green] {result}")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
    
    # Clean up test directory
    try:
        test_file = os.path.join(test_dir, "test.txt")
        if os.path.exists(test_file):
            os.remove(test_file)
            console.print(f"[green]✓[/green] Deleted test file: {test_file}")
        
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
            console.print(f"[green]✓[/green] Deleted test directory: {test_dir}")
    except Exception as e:
        console.print(f"[red]Error during cleanup: {str(e)}[/red]")
    
    return True

def main():
    """Main function."""
    console.print(Panel.fit("Ollama Shell Filesystem Integration Test", title_align="center"))
    
    if test_filesystem_commands():
        console.print("\n[green]All tests completed successfully![/green]")
    else:
        console.print("\n[red]Tests failed![/red]")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for path handling in the Filesystem MCP client.

This script tests how the Filesystem MCP client handles different types of paths,
including relative paths, absolute paths, and paths with tilde expansion.
"""

import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import the FilesystemMCP client
from filesystem_mcp import get_filesystem_mcp

console = Console()

def test_path_handling():
    """Test how different path formats are handled."""
    console.print(Panel.fit("Testing Path Handling in Filesystem MCP", title_align="center"))
    
    # Get the FilesystemMCP client
    mcp = get_filesystem_mcp()
    
    if not mcp.available:
        console.print("[red]⚠️ Filesystem MCP Server is not available. Starting the server...[/red]")
        # The get_filesystem_mcp function should have attempted to start the server
        mcp = get_filesystem_mcp()
        if not mcp.available:
            console.print("[red]⚠️ Failed to start Filesystem MCP Server. Tests cannot continue.[/red]")
            return False
    
    console.print("[green]✓[/green] Filesystem MCP Server is available")
    
    # Test paths to check
    test_paths = [
        # Relative paths
        "Users",
        "Users/",
        "Users/christopher.bradford",
        "Users/christopher.bradford/",
        
        # Absolute paths
        "/Users",
        "/Users/",
        "/Users/christopher.bradford",
        "/Users/christopher.bradford/",
        
        # Home directory paths
        "~",
        "~/",
        "~/Documents",
        "~/Documents/"
    ]
    
    # Create a table for the results
    table = Table(title="Path Handling Test Results")
    table.add_column("Original Path", style="cyan")
    table.add_column("Items Found", style="green")
    table.add_column("Success", style="yellow")
    table.add_column("Error (if any)", style="red")
    
    # Test each path
    for path in test_paths:
        console.print(f"\n[bold cyan]Testing path:[/bold cyan] {path}")
        
        try:
            result = mcp.list_directory(path)
            success = result.get("success", False)
            entries = result.get("entries", [])
            error = result.get("error", "")
            
            table.add_row(
                path,
                str(len(entries)),
                "✓" if success else "✗",
                error
            )
            
            console.print(f"[green]Found {len(entries)} items in {path}[/green]")
        except Exception as e:
            table.add_row(
                path,
                "0",
                "✗",
                str(e)
            )
            console.print(f"[red]Error: {str(e)}[/red]")
    
    # Display the results table
    console.print(table)
    
    return True

def main():
    """Main function."""
    console.print(Panel.fit("Filesystem MCP Path Handling Test", title_align="center"))
    
    if test_path_handling():
        console.print("\n[green]All tests completed![/green]")
    else:
        console.print("\n[red]Tests failed![/red]")

if __name__ == "__main__":
    main()

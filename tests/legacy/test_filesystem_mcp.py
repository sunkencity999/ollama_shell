#!/usr/bin/env python3
"""
Test script for the Filesystem MCP integration.

This script tests the basic functionality of the Filesystem MCP client
to ensure it can connect to the server and perform file system operations.
"""

import os
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import the FilesystemMCP client
from filesystem_mcp import FilesystemMCP

console = Console()

def test_server_connection():
    """Test connection to the Filesystem MCP Server."""
    console.print(Panel.fit("Testing Server Connection", title_align="center"))
    
    # Create a client instance
    client = FilesystemMCP()
    
    if client.available:
        console.print("[green]✓[/green] Server connection successful")
        return client
    else:
        console.print("[red]✗[/red] Failed to connect to server")
        return None

def test_directory_operations(client):
    """Test directory operations."""
    console.print(Panel.fit("Testing Directory Operations", title_align="center"))
    
    # Create a test directory
    test_dir = os.path.expanduser("~/ollama_shell_test")
    
    try:
        # Create directory
        result = client.create_directory(test_dir)
        if result.get("success", False):
            console.print(f"[green]✓[/green] Created directory: {test_dir}")
        else:
            console.print(f"[red]✗[/red] Failed to create directory: {result.get('error', 'Unknown error')}")
            return False
        
        # List directory
        result = client.list_directory(os.path.dirname(test_dir))
        if "entries" in result:
            console.print(f"[green]✓[/green] Listed directory contents")
            
            # Display directory contents in a table
            table = Table(title=f"Contents of {os.path.dirname(test_dir)}")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Size")
            table.add_column("Modified")
            
            for entry in result["entries"]:
                entry_type = "Directory" if entry["is_dir"] else "File"
                table.add_row(
                    entry["name"],
                    entry_type,
                    str(entry["size"]),
                    entry["modified"]
                )
            
            console.print(table)
        else:
            console.print(f"[red]✗[/red] Failed to list directory: {result.get('error', 'Unknown error')}")
            return False
        
        return True
    except Exception as e:
        console.print(f"[red]Error during directory operations: {str(e)}[/red]")
        return False

def test_file_operations(client):
    """Test file operations."""
    console.print(Panel.fit("Testing File Operations", title_align="center"))
    
    # Create a test file
    test_dir = os.path.expanduser("~/ollama_shell_test")
    test_file = os.path.join(test_dir, "test_file.txt")
    
    try:
        # Write to file
        content = "This is a test file created by the Filesystem MCP client.\n"
        result = client.write_file(test_file, content)
        if result.get("success", False):
            console.print(f"[green]✓[/green] Created file: {test_file}")
        else:
            console.print(f"[red]✗[/red] Failed to create file: {result.get('error', 'Unknown error')}")
            return False
        
        # Append to file
        append_content = "This line was appended to the file.\n"
        result = client.append_file(test_file, append_content)
        if result.get("success", False):
            console.print(f"[green]✓[/green] Appended to file: {test_file}")
        else:
            console.print(f"[red]✗[/red] Failed to append to file: {result.get('error', 'Unknown error')}")
            return False
        
        # Read file
        result = client.read_file(test_file)
        if "content" in result:
            console.print(f"[green]✓[/green] Read file content")
            console.print(Panel(result["content"], title="File Content"))
        else:
            console.print(f"[red]✗[/red] Failed to read file: {result.get('error', 'Unknown error')}")
            return False
        
        # Analyze text
        result = client.analyze_text(test_file)
        if result.get("success", False):
            console.print(f"[green]✓[/green] Analyzed text file")
            
            # Display analysis results
            table = Table(title="Text Analysis Results")
            table.add_column("Property")
            table.add_column("Value")
            
            for key, value in result.items():
                if key not in ["success", "path"]:
                    table.add_row(key, str(value))
            
            console.print(table)
        else:
            console.print(f"[red]✗[/red] Failed to analyze text: {result.get('error', 'Unknown error')}")
            return False
        
        # Calculate hash
        result = client.calculate_hash(test_file)
        if result.get("success", False):
            console.print(f"[green]✓[/green] Calculated file hash: {result['hash']}")
        else:
            console.print(f"[red]✗[/red] Failed to calculate hash: {result.get('error', 'Unknown error')}")
            return False
        
        return True
    except Exception as e:
        console.print(f"[red]Error during file operations: {str(e)}[/red]")
        return False

def cleanup(client):
    """Clean up test files and directories."""
    console.print(Panel.fit("Cleaning Up", title_align="center"))
    
    test_dir = os.path.expanduser("~/ollama_shell_test")
    test_file = os.path.join(test_dir, "test_file.txt")
    
    try:
        # Delete the test file using os.remove (since our MCP doesn't have delete)
        if os.path.exists(test_file):
            os.remove(test_file)
            console.print(f"[green]✓[/green] Deleted test file: {test_file}")
        
        # Delete the test directory using os.rmdir
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
            console.print(f"[green]✓[/green] Deleted test directory: {test_dir}")
        
        return True
    except Exception as e:
        console.print(f"[red]Error during cleanup: {str(e)}[/red]")
        return False

def test_path_handling(client):
    """Test path handling for different path formats."""
    console.print(Panel.fit("Testing Path Handling", title_align="center"))
    
    # Create a test directory in the user's home directory
    test_dir = os.path.expanduser("~/ollama_shell_test")
    test_subdir = os.path.join(test_dir, "subdir")
    
    try:
        # Ensure the test directory exists
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        
        # Create a subdirectory for testing
        if not os.path.exists(test_subdir):
            os.makedirs(test_subdir)
        
        # Create a test file in the subdirectory
        test_file = os.path.join(test_subdir, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("This is a test file for path handling.\n")
        
        # Test paths to check
        test_paths = [
            # Relative paths
            f"Users/{os.path.basename(os.path.expanduser('~'))}/ollama_shell_test",
            f"Users/{os.path.basename(os.path.expanduser('~'))}/ollama_shell_test/subdir",
            
            # Absolute paths
            test_dir,
            test_subdir,
            
            # Home directory paths
            "~/ollama_shell_test",
            "~/ollama_shell_test/subdir",
        ]
        
        # Create a table for the results
        table = Table(title="Path Handling Test Results")
        table.add_column("Path Format", style="cyan")
        table.add_column("Original Path", style="cyan")
        table.add_column("Items Found", style="green")
        table.add_column("Success", style="yellow")
        
        # Test each path
        for path in test_paths:
            console.print(f"\n[bold cyan]Testing path:[/bold cyan] {path}")
            
            try:
                result = client.list_directory(path)
                success = result.get("success", False)
                entries = result.get("entries", [])
                
                path_format = "Relative" if not path.startswith(("/", "~")) else "Absolute" if path.startswith("/") else "Home"
                
                table.add_row(
                    path_format,
                    path,
                    str(len(entries)),
                    "✓" if success else "✗"
                )
                
                console.print(f"[green]Found {len(entries)} items in {path}[/green]")
            except Exception as e:
                table.add_row(
                    "Unknown",
                    path,
                    "0",
                    "✗"
                )
                console.print(f"[red]Error: {str(e)}[/red]")
        
        # Display the results table
        console.print(table)
        
        # Test file operations with different path formats
        console.print("\n[bold]Testing file operations with different path formats[/bold]")
        
        # Paths to test file operations with
        file_paths = [
            # Absolute path
            test_file,
            # Relative path
            f"Users/{os.path.basename(os.path.expanduser('~'))}/ollama_shell_test/subdir/test_file.txt",
            # Home directory path
            "~/ollama_shell_test/subdir/test_file.txt"
        ]
        
        file_ops_table = Table(title="File Operations with Different Path Formats")
        file_ops_table.add_column("Path Format", style="cyan")
        file_ops_table.add_column("Operation", style="magenta")
        file_ops_table.add_column("Path", style="cyan")
        file_ops_table.add_column("Success", style="yellow")
        
        for file_path in file_paths:
            path_format = "Relative" if not file_path.startswith(("/", "~")) else "Absolute" if file_path.startswith("/") else "Home"
            
            # Test read operation
            try:
                result = client.read_file(file_path)
                success = "content" in result
                file_ops_table.add_row(
                    path_format,
                    "Read",
                    file_path,
                    "✓" if success else "✗"
                )
            except Exception as e:
                file_ops_table.add_row(
                    path_format,
                    "Read",
                    file_path,
                    "✗"
                )
            
            # Test append operation
            try:
                result = client.append_file(file_path, f"Appended with {path_format} path.\n")
                success = result.get("success", False)
                file_ops_table.add_row(
                    path_format,
                    "Append",
                    file_path,
                    "✓" if success else "✗"
                )
            except Exception as e:
                file_ops_table.add_row(
                    path_format,
                    "Append",
                    file_path,
                    "✗"
                )
        
        # Display the file operations results table
        console.print(file_ops_table)
        
        return True
    except Exception as e:
        console.print(f"[red]Error during path handling tests: {str(e)}[/red]")
        return False

def main():
    """Main function."""
    console.print(Panel.fit("Filesystem MCP Integration Test", title_align="center"))
    
    # Test server connection
    client = test_server_connection()
    if not client:
        return
    
    # Test path handling (our new test for the path handling improvements)
    if not test_path_handling(client):
        return
    
    # Test directory operations
    if not test_directory_operations(client):
        return
    
    # Test file operations
    if not test_file_operations(client):
        return
    
    # Clean up
    cleanup(client)
    
    console.print("\n[green]All tests completed successfully![/green]")

if __name__ == "__main__":
    main()

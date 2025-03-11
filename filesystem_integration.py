#!/usr/bin/env python3
"""
Filesystem Integration for Ollama Shell

This module integrates filesystem operations with the chat interface,
allowing the LLM to perform file system operations directly.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax

from filesystem_mcp import get_filesystem_mcp, FilesystemMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("filesystem_integration")

# Rich console for pretty output
console = Console()

class FilesystemIntegration:
    """
    Integration layer between Ollama Shell and the Filesystem MCP Server.
    Provides methods for handling filesystem commands in the chat interface.
    """
    
    def __init__(self, mcp_url: str = "http://localhost:8000"):
        """
        Initialize the filesystem integration.
        
        Args:
            mcp_url: URL of the Filesystem MCP Server
        """
        self.mcp = get_filesystem_mcp(mcp_url)
        self.available = self.mcp.available
        
        # Command handlers
        self.command_handlers = {
            "ls": self.handle_list_directory,
            "list": self.handle_list_directory,
            "mkdir": self.handle_create_directory,
            "read": self.handle_read_file,
            "write": self.handle_write_file,
            "append": self.handle_append_file,
            "analyze": self.handle_analyze_text,
            "hash": self.handle_calculate_hash,
            "duplicates": self.handle_find_duplicates,
            "zip": self.handle_create_zip,
            "unzip": self.handle_extract_zip,
            "help": self.handle_help,
            "status": self.handle_status,
        }
    
    def handle_command(self, command: str, args: List[str]) -> str:
        """
        Handle a filesystem command.
        
        Args:
            command: The command to handle
            args: List of command arguments
            
        Returns:
            Response message for the chat
        """
        if not self.available:
            return "⚠️ Filesystem MCP Server is not available. Please start the server and try again."
        
        handler = self.command_handlers.get(command.lower())
        if handler:
            try:
                return handler(args)
            except Exception as e:
                logger.error(f"Error handling command {command}: {str(e)}")
                return f"⚠️ Error: {str(e)}"
        else:
            return f"⚠️ Unknown command: {command}. Type '/fs help' for available commands."
    
    def handle_list_directory(self, args: List[str]) -> str:
        """Handle the list directory command."""
        if not args:
            path = os.getcwd()
        else:
            path = args[0]
        
        try:
            result = self.mcp.list_directory(path)
            
            # Create a table for the directory contents
            table = Table(title=f"Directory: {path}")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Size", style="yellow")
            table.add_column("Modified", style="magenta")
            
            entries = result.get("entries", [])
            for item in entries:
                item_type = "Directory" if item.get("is_dir") else "File"
                size = str(item.get("size", "")) if not item.get("is_dir") else ""
                modified = item.get("modified", "")
                table.add_row(item.get("name", ""), item_type, size, modified)
            
            console.print(table)
            return f"Listed {len(entries)} items in {path}"
        except Exception as e:
            return f"⚠️ Error listing directory: {str(e)}"
    
    def handle_create_directory(self, args: List[str]) -> str:
        """Handle the create directory command."""
        if not args:
            return "⚠️ Missing directory path. Usage: /fs mkdir <path>"
        
        path = args[0]
        try:
            result = self.mcp.create_directory(path)
            return f"✅ Directory created: {path}"
        except Exception as e:
            return f"⚠️ Error creating directory: {str(e)}"
    
    def handle_read_file(self, args: List[str]) -> str:
        """Handle the read file command."""
        if not args:
            return "⚠️ Missing file path. Usage: /fs read <path> [encoding]"
        
        path = args[0]
        encoding = args[1] if len(args) > 1 else "utf-8"
        
        try:
            result = self.mcp.read_file(path, encoding)
            content = result.get("content", "")
            
            # Detect file type for syntax highlighting
            file_ext = os.path.splitext(path)[1].lstrip('.')
            if file_ext:
                syntax = Syntax(content, file_ext, line_numbers=True)
                console.print(Panel(syntax, title=path))
            else:
                console.print(Panel(content, title=path))
            
            return f"Read {len(content)} characters from {path}"
        except Exception as e:
            return f"⚠️ Error reading file: {str(e)}"
    
    def handle_write_file(self, args: List[str]) -> str:
        """Handle the write file command."""
        if len(args) < 2:
            return "⚠️ Missing arguments. Usage: /fs write <path> <content> [encoding]"
        
        path = args[0]
        content = args[1]
        encoding = args[2] if len(args) > 2 else "utf-8"
        
        try:
            result = self.mcp.write_file(path, content, encoding)
            return f"✅ File written: {path} ({len(content)} characters)"
        except Exception as e:
            return f"⚠️ Error writing file: {str(e)}"
    
    def handle_append_file(self, args: List[str]) -> str:
        """Handle the append file command."""
        if len(args) < 2:
            return "⚠️ Missing arguments. Usage: /fs append <path> <content> [encoding]"
        
        path = args[0]
        content = args[1]
        encoding = args[2] if len(args) > 2 else "utf-8"
        
        try:
            result = self.mcp.append_file(path, content, encoding)
            return f"✅ Content appended to file: {path} ({len(content)} characters)"
        except Exception as e:
            return f"⚠️ Error appending to file: {str(e)}"
    
    def handle_analyze_text(self, args: List[str]) -> str:
        """Handle the analyze text command."""
        if not args:
            return "⚠️ Missing file path. Usage: /fs analyze <path>"
        
        path = args[0]
        try:
            result = self.mcp.analyze_text(path)
            
            # Create a table for the analysis results
            table = Table(title=f"Text Analysis: {path}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            for key, value in result.items():
                if key != "success":
                    table.add_row(key, str(value))
            
            console.print(table)
            return f"Analyzed text file: {path}"
        except Exception as e:
            return f"⚠️ Error analyzing text: {str(e)}"
    
    def handle_calculate_hash(self, args: List[str]) -> str:
        """Handle the calculate hash command."""
        if not args:
            return "⚠️ Missing file path. Usage: /fs hash <path> [algorithm]"
        
        path = args[0]
        algorithm = args[1] if len(args) > 1 else "sha256"
        
        try:
            result = self.mcp.calculate_hash(path, algorithm)
            hash_value = result.get("hash", "")
            return f"Hash ({algorithm}) for {path}: {hash_value}"
        except Exception as e:
            return f"⚠️ Error calculating hash: {str(e)}"
    
    def handle_find_duplicates(self, args: List[str]) -> str:
        """Handle the find duplicates command."""
        if not args:
            return "⚠️ Missing directory path. Usage: /fs duplicates <directory>"
        
        directory = args[0]
        try:
            result = self.mcp.find_duplicates(directory)
            duplicates = result.get("duplicates", {})
            
            if not duplicates:
                return f"No duplicate files found in {directory}"
            
            # Create a table for the duplicate files
            table = Table(title=f"Duplicate Files in {directory}")
            table.add_column("Hash", style="cyan")
            table.add_column("Files", style="green")
            
            for hash_value, files in duplicates.items():
                table.add_row(hash_value, "\n".join(files))
            
            console.print(table)
            return f"Found {len(duplicates)} sets of duplicate files in {directory}"
        except Exception as e:
            return f"⚠️ Error finding duplicates: {str(e)}"
    
    def handle_create_zip(self, args: List[str]) -> str:
        """Handle the create zip command."""
        if len(args) < 2:
            return "⚠️ Missing arguments. Usage: /fs zip <output_path> <source_path1> [source_path2 ...]"
        
        output_path = args[0]
        source_paths = args[1:]
        
        try:
            result = self.mcp.create_zip(source_paths, output_path)
            return f"✅ Created ZIP archive: {output_path} with {len(source_paths)} source paths"
        except Exception as e:
            return f"⚠️ Error creating ZIP archive: {str(e)}"
    
    def handle_extract_zip(self, args: List[str]) -> str:
        """Handle the extract zip command."""
        if len(args) < 2:
            return "⚠️ Missing arguments. Usage: /fs unzip <zip_path> <output_directory>"
        
        zip_path = args[0]
        output_directory = args[1]
        
        try:
            result = self.mcp.extract_zip(zip_path, output_directory)
            extracted_files = result.get("extracted_files", [])
            return f"✅ Extracted ZIP archive: {zip_path} to {output_directory} ({len(extracted_files)} files)"
        except Exception as e:
            return f"⚠️ Error extracting ZIP archive: {str(e)}"
    
    def handle_help(self, args: List[str]) -> str:
        """Handle the help command."""
        help_text = """
# Filesystem Commands

## Directory Operations
- `/fs ls [path]` - List directory contents
- `/fs mkdir <path>` - Create a new directory

## File Operations
- `/fs read <path> [encoding]` - Read file content
- `/fs write <path> <content> [encoding]` - Write content to a file
- `/fs append <path> <content> [encoding]` - Append content to a file

## Analysis Operations
- `/fs analyze <path>` - Analyze text file properties
- `/fs hash <path> [algorithm]` - Calculate file hash
- `/fs duplicates <directory>` - Find duplicate files

## Compression Operations
- `/fs zip <output_path> <source_path1> [source_path2 ...]` - Create a ZIP archive
- `/fs unzip <zip_path> <output_directory>` - Extract a ZIP archive

## System
- `/fs status` - Check Filesystem MCP Server status
- `/fs help` - Show this help message
"""
        console.print(Markdown(help_text))
        return "Filesystem commands help displayed"
    
    def handle_status(self, args: List[str]) -> str:
        """Handle the status command."""
        if self.available:
            return "✅ Filesystem MCP Server is available and connected"
        else:
            return "⚠️ Filesystem MCP Server is not available"


# Singleton instance for use throughout the application
_fs_integration_instance = None

def get_filesystem_integration(mcp_url: str = "http://localhost:8000") -> FilesystemIntegration:
    """
    Get the singleton instance of the FilesystemIntegration.
    
    Args:
        mcp_url: URL of the Filesystem MCP Server
        
    Returns:
        FilesystemIntegration instance
    """
    global _fs_integration_instance
    if _fs_integration_instance is None:
        _fs_integration_instance = FilesystemIntegration(mcp_url)
    return _fs_integration_instance


def filesystem_mode():
    """
    Enter a filesystem mode where users can execute filesystem commands.
    This provides a simple filesystem interface within Ollama Shell.
    """
    fs = get_filesystem_integration()
    
    if not fs.available:
        console.print("[red]⚠️ Filesystem MCP Server is not available. Please start the server and try again.[/red]")
        return
    
    console.print("\n[bold cyan]Filesystem Mode[/bold cyan]")
    console.print("[yellow]Type commands to execute them. Type 'exit' to return to the main menu.[/yellow]")
    console.print("[yellow]Current directory: [green]{0}[/green][/yellow]".format(os.getcwd()))
    
    # Display help on startup
    fs.handle_help([])
    
    try:
        while True:
            # Get command from user
            cmd_input = console.input("\n[bold green]fs>[/bold green] ")
            
            # Exit filesystem mode
            if cmd_input.lower() in ['exit', 'quit', 'q']:
                break
                
            # Handle help command
            if cmd_input.lower() in ['help', '?']:
                fs.handle_help([])
                continue
                
            # Parse command and arguments
            parts = cmd_input.split()
            if not parts:
                continue
                
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Handle the command
            response = fs.handle_command(command, args)
            if response:
                console.print(f"[dim]{response}[/dim]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Filesystem mode exited.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error in filesystem mode: {str(e)}[/red]")


def handle_fs_command(command_parts: List[str]) -> str:
    """
    Handle a filesystem command from the chat interface.
    
    Args:
        command_parts: List of command parts (first is the subcommand)
        
    Returns:
        Response message for the chat
    """
    fs = get_filesystem_integration()
    
    if not command_parts:
        return fs.handle_help([])
    
    subcommand = command_parts[0]
    args = command_parts[1:] if len(command_parts) > 1 else []
    
    return fs.handle_command(subcommand, args)

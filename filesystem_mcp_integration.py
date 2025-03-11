#!/usr/bin/env python3
"""
Filesystem MCP Integration for Ollama Shell

This module integrates the Model Context Protocol (MCP) Filesystem server
with Ollama Shell, allowing LLMs to interact with the filesystem through
natural language.
"""

import os
import sys
import json
import logging
import subprocess
import threading
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("filesystem_mcp_integration")

# Import MCP client libraries
try:
    from mcp.client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCP library not available. Using fallback implementation.")
    MCP_AVAILABLE = False

# Import Ollama API client
import requests

# Import filesystem operations directly when MCP is not available
from filesystem_mcp_server_simple import (
    is_path_allowed, list_directory, create_directory,
    read_file, write_file, append_file, analyze_text, calculate_hash,
    find_duplicates, create_zip, extract_zip, config
)

class FilesystemMCPIntegration:
    """
    Integration between Ollama Shell and the Filesystem MCP Protocol server.
    Allows LLMs to interact with the filesystem through natural language.
    """
    
    def __init__(self, server_host: str = "localhost", server_port: int = 8765):
        """
        Initialize the Filesystem MCP integration.
        
        Args:
            server_host: Host where the Filesystem MCP Protocol server is running
            server_port: Port where the Filesystem MCP Protocol server is running
        """
        self.server_host = server_host
        self.server_port = server_port
        self.server_url = f"http://{server_host}:{server_port}"
        self.server_process = None
        self.available = False
        
        # Try to connect to the server or use fallback
        self._connect_to_server()
    
    def _connect_to_server(self) -> bool:
        """
        Connect to the Filesystem MCP Protocol server.
        If the server is not available, try to start it.
        If MCP is not available, use the fallback implementation.
        
        Returns:
            bool: True if connected, False otherwise
        """
        # If MCP is not available, use the fallback implementation
        if not MCP_AVAILABLE:
            logger.info("Using fallback implementation for filesystem operations")
            self.available = True
            return True
        
        try:
            # Create a client to test the connection
            client = MCPClient(self.server_url)
            # Test the connection by getting the server info
            info = client.get_server_info()
            logger.info(f"Connected to Filesystem MCP Protocol server: {info.get('name', 'Unknown')}")
            self.available = True
            return True
        except Exception as e:
            logger.warning(f"Could not connect to Filesystem MCP Protocol server: {str(e)}")
            logger.info("Trying to start the server...")
            
            # Try to start the server
            return self._start_server()
    
    def _start_server(self) -> bool:
        """
        Start the Filesystem MCP Protocol server.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        # If MCP is not available, use the fallback implementation
        if not MCP_AVAILABLE:
            logger.info("Using fallback implementation for filesystem operations")
            self.available = True
            return True
            
        try:
            # Get the path to the server script
            server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filesystem_mcp_protocol.py")
            
            # Check if the server script exists
            if not os.path.exists(server_script):
                logger.error(f"Server script not found: {server_script}")
                return False
            
            # Start the server as a subprocess with a new session to ensure it keeps running
            logger.info(f"Starting Filesystem MCP Protocol server from {server_script}...")
            self.server_process = subprocess.Popen(
                [sys.executable, server_script, str(self.server_port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Ensure the server continues running even if the parent process exits
            )
            
            # Wait for the server to start with increased timeout
            max_attempts = 10  # Try for 10 seconds
            for attempt in range(max_attempts):
                time.sleep(1)
                try:
                    # Check if the process is still running
                    if self.server_process.poll() is not None:
                        stderr = self.server_process.stderr.read().decode('utf-8')
                        logger.error(f"Server process exited with code {self.server_process.poll()}")
                        if stderr:
                            logger.error(f"Server error: {stderr}")
                        return False
                    
                    # Try to connect to the server
                    client = MCPClient(self.server_url)
                    info = client.get_server_info()
                    logger.info(f"Started Filesystem MCP Protocol server: {info.get('name', 'Unknown')}")
                    self.available = True
                    return True
                except Exception as e:
                    logger.debug(f"Waiting for server to start (attempt {attempt+1}/{max_attempts}): {str(e)}")
            
            logger.error("Failed to start Filesystem MCP Protocol server: timed out waiting for server to start")
            return False
        except Exception as e:
            logger.error(f"Error starting Filesystem MCP Protocol server: {str(e)}")
            return False
    
    def get_ollama_client(self, model: Optional[str] = None) -> Optional[dict]:
        """
        Get an Ollama client configuration to use with the Filesystem MCP Protocol server.
        
        Args:
            model: Ollama model to use (optional)
            
        Returns:
            Dictionary with client configuration or None if not available
        """
        if not self.available:
            logger.error("Filesystem MCP Protocol server is not available")
            return None
        
        try:
            # Try to load the default model from config
            default_model = "llama3.2"
            try:
                import json
                config_file = os.path.join(os.path.dirname(__file__), "config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    default_model = config.get("default_model", default_model)
            except Exception as e:
                logger.warning(f"Failed to load config: {str(e)}")
            
            # Create a client configuration for Ollama
            client_config = {
                "model": model if model else default_model,
                "server_url": self.server_url,
                "ollama_api_url": "http://localhost:11434/api"
            }
            return client_config
        except Exception as e:
            logger.error(f"Error creating Ollama client configuration: {str(e)}")
            return None
    
    def execute_natural_language_command(self, command: str, model: Optional[str] = None) -> str:
        """
        Execute a natural language filesystem command using the Ollama API.
        
        Args:
            command: The natural language command to execute
            model: The model to use for the command (optional)
            
        Returns:
            The result of the command execution
        """
        if not self.available:
            return "Filesystem MCP Protocol is not available. Please ensure the server is running."
        
        try:
            # Get the Ollama client configuration
            client_config = self.get_ollama_client(model if model else "llama3.2")
            if not client_config:
                return "Failed to create Ollama client configuration."
            
            # Prepare the system prompt for filesystem operations with tools
            system_prompt = (
                "You are a helpful assistant with DIRECT access to filesystem operations through specialized tools. "
                "You MUST use these tools to help the user manage their files and directories. "
                "DO NOT make up or simulate file operations - you have REAL tools to access the filesystem. "
                "Always explain what you're doing and be careful with destructive operations. "
                "You have access to the following filesystem tools:\n"
                "1. list_directory(path): Lists all files and directories at the specified path\n"
                "2. create_directory(path): Creates a new directory at the specified path\n"
                "3. read_file(path): Reads the content of a file at the specified path\n"
                "4. write_file(path, content): Writes content to a file at the specified path\n"
                "5. delete_file(path): Deletes a file at the specified path (use with caution)\n"
                "6. find_files(pattern, directory): Finds files matching a pattern in the specified directory\n"
                "7. get_file_info(path): Gets information about a file (size, type, etc.)\n\n"
                "When the user asks about files or directories, ALWAYS use these tools to provide accurate information. "
                "NEVER make up file names or content. Use the tools to get real information from the filesystem."
            )
            
            # Log the request for debugging
            logger.info(f"Sending request to Ollama API with model: {client_config['model']}")
            
            # Use the same API endpoint and format as the main Ollama Shell application
            try:
                # First, let's prepare the actual filesystem tools that will be available to the model
                # This is a simulation of what would happen in a real implementation with the MCP server
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "list_directory",
                            "description": "Lists all files and directories at the specified path",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "The path to list files from"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "description": "Reads the content of a file at the specified path",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "The path to the file to read"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "find_files",
                            "description": "Finds files matching a pattern in the specified directory",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "pattern": {
                                        "type": "string",
                                        "description": "The pattern to match files against"
                                    },
                                    "directory": {
                                        "type": "string",
                                        "description": "The directory to search in"
                                    }
                                },
                                "required": ["pattern", "directory"]
                            }
                        }
                    }
                ]
                
                # Prepare the payload with tools
                payload = {
                    "model": client_config["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": command}
                    ],
                    "options": {
                        "temperature": 0.7,
                        "num_ctx": 8192  # Default context length
                    },
                    "tools": tools,  # Add the tools to the payload
                    "stream": False
                }
                
                # Make the API request
                response = requests.post(
                    f"{client_config['ollama_api_url']}/chat",
                    json=payload
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    try:
                        # Parse the response JSON
                        result = response.json()
                        logger.info(f"Received response from Ollama API: {result}")
                        
                        # Extract the message content from the response
                        if isinstance(result, dict) and "message" in result and "content" in result["message"]:
                            llm_response = result["message"]["content"]
                        else:
                            logger.error(f"Unexpected response format: {result}")
                            llm_response = "Unexpected response format from the model."
                        
                        # Check if the response contains tool calls
                        if "tool_calls" in result["message"]:
                            # Process tool calls and execute filesystem operations
                            return self._handle_tool_calls(result["message"]["tool_calls"], command)
                        else:
                            # If no tool calls, just return the LLM response
                            return llm_response
                    except json.JSONDecodeError as e:
                        # If JSON parsing fails, try to extract content from raw response
                        content = response.text.strip()
                        if content:
                            return content
                        else:
                            error_msg = f"Failed to parse response: {e}"
                            logger.error(error_msg)
                            return error_msg
                else:
                    error_msg = f"Error: Received status code {response.status_code} from Ollama API."
                    logger.error(f"{error_msg} Response: {response.text}")
                    return error_msg
            except Exception as e:
                error_msg = f"Error communicating with Ollama API: {str(e)}"
                logger.error(error_msg)
                return error_msg
        except Exception as e:
            logger.error(f"Error executing natural language command: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def _handle_tool_calls(self, tool_calls, original_command):
        """Process tool calls and execute filesystem operations.
        
        Args:
            tool_calls: List of tool calls from the LLM response
            original_command: The original natural language command
            
        Returns:
            A formatted response with the results of the tool calls
        """
        if not tool_calls or not isinstance(tool_calls, list):
            return "No valid tool calls received from the model."
        
        # Initialize response
        response_parts = []
        
        # Process each tool call
        for tool_call in tool_calls:
            try:
                # Extract tool information
                if not isinstance(tool_call, dict) or 'function' not in tool_call:
                    response_parts.append("Invalid tool call format.")
                    continue
                
                function_info = tool_call.get('function', {})
                name = function_info.get('name')
                arguments = function_info.get('arguments', '{}')
                
                # Parse arguments
                try:
                    if isinstance(arguments, str):
                        args = json.loads(arguments)
                    else:
                        args = arguments
                except json.JSONDecodeError:
                    response_parts.append(f"Error: Could not parse arguments for {name}")
                    continue
                
                # Execute the appropriate filesystem operation based on the tool name
                if name == "list_directory":
                    result = self._list_directory(args.get('path', ''))
                    response_parts.append(f"Directory listing for {args.get('path', '')}:\n{result}")
                
                elif name == "read_file":
                    result = self._read_file(args.get('path', ''))
                    response_parts.append(f"Content of {args.get('path', '')}:\n{result}")
                
                elif name == "find_files":
                    result = self._find_files(args.get('pattern', ''), args.get('directory', ''))
                    response_parts.append(f"Files matching {args.get('pattern', '')} in {args.get('directory', '')}:\n{result}")
                
                elif name == "create_directory":
                    result = self._create_directory(args.get('path', ''))
                    response_parts.append(result)
                
                elif name == "write_file":
                    result = self._write_file(args.get('path', ''), args.get('content', ''))
                    response_parts.append(result)
                
                elif name == "delete_file":
                    result = self._delete_file(args.get('path', ''))
                    response_parts.append(result)
                
                elif name == "get_file_info":
                    result = self._get_file_info(args.get('path', ''))
                    response_parts.append(f"Information for {args.get('path', '')}:\n{result}")
                
                else:
                    response_parts.append(f"Unknown tool: {name}")
            
            except Exception as e:
                response_parts.append(f"Error executing tool {name}: {str(e)}")
        
        # Join all response parts with newlines
        return "\n\n".join(response_parts)
    
    def _list_directory(self, path):
        """List files and directories at the specified path."""
        try:
            # Handle special paths
            if path.startswith('/') and not path.startswith('/Users') and not path.startswith('/home'):
                # For paths like '/Documents', '/Desktop', etc., assume they're in the user's home directory
                if path in ['/Documents', '/Desktop', '/Downloads', '/Pictures', '/Music', '/Videos', '/Movies']:
                    path = os.path.join('~', path[1:])  # Convert '/Documents' to '~/Documents'
            
            # Expand user path (e.g., ~)
            expanded_path = os.path.expanduser(path)
            
            # Check if path exists
            if not os.path.exists(expanded_path):
                # Try a few common alternatives
                alternatives = [
                    os.path.expanduser(f"~{path}"),  # Try ~/path
                    os.path.expanduser(f"~/Documents{path}"),  # Try ~/Documents/path
                    os.path.join(os.getcwd(), path.lstrip('/')),  # Try current directory + path
                ]
                
                for alt_path in alternatives:
                    if os.path.exists(alt_path):
                        expanded_path = alt_path
                        break
                else:
                    return f"Error: Path '{path}' does not exist. I tried several common locations but couldn't find it."
            
            # Check if path is a directory
            if not os.path.isdir(expanded_path):
                return f"Error: Path '{path}' is not a directory."
            
            # List files and directories
            items = os.listdir(expanded_path)
            
            # Format the result
            result = []
            for item in items:
                item_path = os.path.join(expanded_path, item)
                item_type = "Directory" if os.path.isdir(item_path) else "File"
                item_size = os.path.getsize(item_path) if os.path.isfile(item_path) else "-"
                result.append(f"{item} ({item_type}, Size: {item_size} bytes)")
            
            if not result:
                return "Directory is empty."
            
            return "\n".join(result)
        
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def _read_file(self, path):
        """Read the content of a file at the specified path."""
        try:
            # Handle special paths
            if path.startswith('/') and not path.startswith('/Users') and not path.startswith('/home'):
                # For paths like '/Documents/file.txt', assume they're in the user's home directory
                for special_dir in ['/Documents', '/Desktop', '/Downloads', '/Pictures', '/Music', '/Videos', '/Movies']:
                    if path.startswith(special_dir):
                        path = os.path.join('~', path[1:])  # Convert '/Documents/file.txt' to '~/Documents/file.txt'
                        break
            
            # Expand user path (e.g., ~)
            expanded_path = os.path.expanduser(path)
            
            # Check if path exists
            if not os.path.exists(expanded_path):
                # Try a few common alternatives
                alternatives = [
                    os.path.expanduser(f"~{path}"),  # Try ~/path
                    os.path.expanduser(f"~/Documents{path}"),  # Try ~/Documents/path
                    os.path.join(os.getcwd(), path.lstrip('/')),  # Try current directory + path
                ]
                
                for alt_path in alternatives:
                    if os.path.exists(alt_path):
                        expanded_path = alt_path
                        break
                else:
                    return f"Error: File '{path}' does not exist. I tried several common locations but couldn't find it."
            
            # Check if path is a file
            if not os.path.isfile(expanded_path):
                return f"Error: Path '{path}' is not a file."
            
            # Read file content
            with open(expanded_path, 'r') as f:
                content = f.read()
            
            return content
        
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def _find_files(self, pattern, directory):
        """Find files matching a pattern in the specified directory."""
        try:
            # Handle special paths
            if directory.startswith('/') and not directory.startswith('/Users') and not directory.startswith('/home'):
                # For paths like '/Documents', '/Desktop', etc., assume they're in the user's home directory
                if directory in ['/Documents', '/Desktop', '/Downloads', '/Pictures', '/Music', '/Videos', '/Movies']:
                    directory = os.path.join('~', directory[1:])  # Convert '/Documents' to '~/Documents'
            
            # Expand user path (e.g., ~)
            expanded_dir = os.path.expanduser(directory)
            
            # Check if directory exists
            if not os.path.exists(expanded_dir):
                # Try a few common alternatives
                alternatives = [
                    os.path.expanduser(f"~{directory}"),  # Try ~/directory
                    os.path.expanduser(f"~/Documents{directory}"),  # Try ~/Documents/directory
                    os.path.join(os.getcwd(), directory.lstrip('/')),  # Try current directory + directory
                ]
                
                for alt_path in alternatives:
                    if os.path.exists(alt_path):
                        expanded_dir = alt_path
                        break
                else:
                    return f"Error: Directory '{directory}' does not exist. I tried several common locations but couldn't find it."
            
            # Check if path is a directory
            if not os.path.isdir(expanded_dir):
                return f"Error: Path '{directory}' is not a directory."
            
            # Find files matching the pattern
            import glob
            matches = glob.glob(os.path.join(expanded_dir, pattern))
            
            # Format the result
            if not matches:
                return f"No files matching '{pattern}' found in '{directory}'."
            
            result = []
            for match in matches:
                item_type = "Directory" if os.path.isdir(match) else "File"
                item_size = os.path.getsize(match) if os.path.isfile(match) else "-"
                result.append(f"{os.path.basename(match)} ({item_type}, Size: {item_size} bytes)")
            
            return "\n".join(result)
        
        except Exception as e:
            return f"Error finding files: {str(e)}"
    
    def _create_directory(self, path):
        """Create a new directory at the specified path."""
        try:
            # Handle special paths
            if path.startswith('/') and not path.startswith('/Users') and not path.startswith('/home'):
                # For paths like '/Documents', '/Desktop', etc., assume they're in the user's home directory
                if path in ['/Documents', '/Desktop', '/Downloads', '/Pictures', '/Music', '/Videos', '/Movies']:
                    path = os.path.join('~', path[1:])  # Convert '/Documents' to '~/Documents'
            
            # Handle paths that should be absolute but don't start with /
            if path.startswith('Users/') or path.startswith('home/'):
                path = '/' + path  # Convert 'Users/...' to '/Users/...'
            
            # Expand user path (e.g., ~)
            expanded_path = os.path.expanduser(path)
            
            # If the path doesn't start with /, make it absolute
            if not os.path.isabs(expanded_path):
                # Check if it's a path like 'Documents/folder'
                if path.split('/')[0] in ['Documents', 'Desktop', 'Downloads', 'Pictures', 'Music', 'Videos', 'Movies']:
                    expanded_path = os.path.join(os.path.expanduser('~'), path)
            
            # Check if path already exists
            if os.path.exists(expanded_path):
                return f"Error: Path '{path}' already exists."
            
            # Create directory
            os.makedirs(expanded_path, exist_ok=True)
            
            return f"Directory '{path}' created successfully at {expanded_path}"
        
        except Exception as e:
            return f"Error creating directory: {str(e)}"
    
    def _write_file(self, path, content):
        """Write content to a file at the specified path."""
        try:
            # Handle special paths
            if path.startswith('/') and not path.startswith('/Users') and not path.startswith('/home'):
                # For paths like '/Documents/file.txt', assume they're in the user's home directory
                for special_dir in ['/Documents', '/Desktop', '/Downloads', '/Pictures', '/Music', '/Videos', '/Movies']:
                    if path.startswith(special_dir):
                        path = os.path.join('~', path[1:])  # Convert '/Documents/file.txt' to '~/Documents/file.txt'
                        break
            
            # Handle paths that should be absolute but don't start with /
            if path.startswith('Users/') or path.startswith('home/'):
                path = '/' + path  # Convert 'Users/...' to '/Users/...'
            
            # Expand user path (e.g., ~)
            expanded_path = os.path.expanduser(path)
            
            # If the path doesn't start with /, make it absolute
            if not os.path.isabs(expanded_path):
                # Check if it's a path like 'Documents/file.txt'
                if path.split('/')[0] in ['Documents', 'Desktop', 'Downloads', 'Pictures', 'Music', 'Videos', 'Movies']:
                    expanded_path = os.path.join(os.path.expanduser('~'), path)
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(expanded_path), exist_ok=True)
            
            # Write content to file
            with open(expanded_path, 'w') as f:
                f.write(content)
            
            return f"File '{path}' written successfully at {expanded_path}"
        
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def _delete_file(self, path):
        """Delete a file at the specified path."""
        try:
            # Handle special paths
            if path.startswith('/') and not path.startswith('/Users') and not path.startswith('/home'):
                # For paths like '/Documents/file.txt', assume they're in the user's home directory
                for special_dir in ['/Documents', '/Desktop', '/Downloads', '/Pictures', '/Music', '/Videos', '/Movies']:
                    if path.startswith(special_dir):
                        path = os.path.join('~', path[1:])  # Convert '/Documents/file.txt' to '~/Documents/file.txt'
                        break
            
            # Handle paths that should be absolute but don't start with /
            if path.startswith('Users/') or path.startswith('home/'):
                path = '/' + path  # Convert 'Users/...' to '/Users/...'
            
            # Expand user path (e.g., ~)
            expanded_path = os.path.expanduser(path)
            
            # If the path doesn't start with /, make it absolute
            if not os.path.isabs(expanded_path):
                # Check if it's a path like 'Documents/file.txt'
                if path.split('/')[0] in ['Documents', 'Desktop', 'Downloads', 'Pictures', 'Music', 'Videos', 'Movies']:
                    expanded_path = os.path.join(os.path.expanduser('~'), path)
            
            # Check if path exists
            if not os.path.exists(expanded_path):
                return f"Error: Path '{path}' does not exist."
            
            # Check if path is a file
            if not os.path.isfile(expanded_path):
                return f"Error: Path '{path}' is not a file."
            
            # Delete file
            os.remove(expanded_path)
            
            return f"File '{path}' deleted successfully from {expanded_path}"
        
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    def _get_file_info(self, path):
        """Get information about a file."""
        try:
            # Expand user path (e.g., ~)
            expanded_path = os.path.expanduser(path)
            
            # Check if path exists
            if not os.path.exists(expanded_path):
                return f"Error: Path '{path}' does not exist."
            
            # Get file information
            import datetime
            stat_info = os.stat(expanded_path)
            
            # Format the result
            result = [
                f"Path: {path}",
                f"Type: {'Directory' if os.path.isdir(expanded_path) else 'File'}",
                f"Size: {stat_info.st_size} bytes",
                f"Created: {datetime.datetime.fromtimestamp(stat_info.st_ctime)}",
                f"Modified: {datetime.datetime.fromtimestamp(stat_info.st_mtime)}",
                f"Accessed: {datetime.datetime.fromtimestamp(stat_info.st_atime)}",
                f"Permissions: {oct(stat_info.st_mode)[-3:]}"
            ]
            
            return "\n".join(result)
        
        except Exception as e:
            return f"Error getting file information: {str(e)}"
    
    def shutdown(self):
        """Shutdown the Filesystem MCP Protocol server if it was started by this integration."""
        if self.server_process:
            logger.info("Shutting down Filesystem MCP Protocol server")
            self.server_process.terminate()
            self.server_process = None
            self.available = False

# Singleton instance for use throughout the application
_fs_mcp_integration_instance = None

def get_filesystem_mcp_integration(server_host: str = "localhost", server_port: int = 8765) -> FilesystemMCPIntegration:
    """
    Get the singleton instance of the FilesystemMCPIntegration.
    If the server is not running, it will be started automatically.
    
    Args:
        server_host: Host where the Filesystem MCP Protocol server is running
        server_port: Port where the Filesystem MCP Protocol server is running
        
    Returns:
        FilesystemMCPIntegration instance
    """
    global _fs_mcp_integration_instance
    
    if _fs_mcp_integration_instance is None:
        _fs_mcp_integration_instance = FilesystemMCPIntegration(server_host, server_port)
        
        # If the server is not available, try to start it
        if not _fs_mcp_integration_instance.available and MCP_AVAILABLE:
            logger.info("Filesystem MCP Protocol server not available, attempting to start it...")
            _fs_mcp_integration_instance.start_server()
    
    return _fs_mcp_integration_instance

def handle_natural_language_fs_command(command: str, model: Optional[str] = None) -> str:
    """
    Handle a natural language filesystem command.
    
    Args:
        command: Natural language command to execute
        model: Ollama model to use (optional)
        
    Returns:
        Response from the LLM
    """
    integration = get_filesystem_mcp_integration()
    return integration.execute_natural_language_command(command, model)

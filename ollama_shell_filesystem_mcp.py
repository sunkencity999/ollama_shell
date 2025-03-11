#!/usr/bin/env python3
"""
Ollama Shell Filesystem MCP Integration

This module integrates the Filesystem MCP Protocol with Ollama Shell,
allowing users to interact with the filesystem using natural language
through the chat interface.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ollama_shell_filesystem_mcp")

# Import the Filesystem MCP Protocol integration
try:
    from filesystem_mcp_integration import get_filesystem_mcp_integration
    FILESYSTEM_MCP_AVAILABLE = True
except ImportError:
    FILESYSTEM_MCP_AVAILABLE = False
    logger.warning("Filesystem MCP Protocol integration not available")

class OllamaShellFilesystemMCP:
    """
    Integration between Ollama Shell and the Filesystem MCP Protocol.
    Allows users to interact with the filesystem using natural language
    through the chat interface.
    """
    
    def __init__(self, default_model: str = None):
        """
        Initialize the Ollama Shell Filesystem MCP integration.
        
        Args:
            default_model: Default Ollama model to use for natural language commands
        """
        self.available = False
        
        # Load the configuration to get the default model if not provided
        if not default_model:
            try:
                config_file = os.path.expanduser("~/.ollama_shell/config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    self.default_model = config.get("default_model", "llama3.2")
                else:
                    self.default_model = "llama3.2"
            except Exception as e:
                logger.warning(f"Failed to load config: {str(e)}")
                self.default_model = "llama3.2"
        else:
            self.default_model = default_model
        
        # Check if Filesystem MCP Protocol integration is available
        if not FILESYSTEM_MCP_AVAILABLE:
            logger.warning("Filesystem MCP Protocol integration not available")
            return
        
        # Get the Filesystem MCP Protocol integration
        self.integration = get_filesystem_mcp_integration()
        self.available = self.integration.available
        
        if self.available:
            logger.info("Filesystem MCP Protocol integration available")
        else:
            logger.warning("Filesystem MCP Protocol integration not available")
    
    def set_default_model(self, model: str):
        """
        Set the default Ollama model to use.
        
        Args:
            model: Ollama model name
        """
        self.default_model = model
    
    def handle_command(self, command: str, model: Optional[str] = None) -> str:
        """
        Handle a natural language filesystem command.
        
        Args:
            command: Natural language command to execute
            model: Ollama model to use (optional, uses default_model if not specified)
            
        Returns:
            Response from the LLM with the results of the filesystem operation
        """
        if not self.available:
            return "Filesystem MCP Protocol integration not available"
        
        # Use the specified model or fall back to the default model
        model_to_use = model if model else self.default_model
        
        try:
            # Handle the command using the integration's execute_natural_language_command method
            result = self.integration.execute_natural_language_command(command, model_to_use)
            
            # Check if we got a response
            if not result or result.strip() == "":
                return "No response from the model. Please try again with a more specific command."
            
            # Format the response for better readability
            formatted_result = f"\n{result}\n"
            
            return formatted_result
        except Exception as e:
            logger.error(f"Error handling command: {str(e)}")
            return f"Error handling command: {str(e)}"
    
    def shutdown(self):
        """Shutdown the Filesystem MCP Protocol integration."""
        if self.available:
            self.integration.shutdown()
            self.available = False

# Singleton instance for use throughout the application
_ollama_shell_filesystem_mcp_instance = None

def get_ollama_shell_filesystem_mcp(default_model: Optional[str] = None) -> OllamaShellFilesystemMCP:
    """
    Get the singleton instance of the OllamaShellFilesystemMCP.
    
    Args:
        default_model: Default Ollama model to use (optional, uses "llama2" if not specified)
        
    Returns:
        OllamaShellFilesystemMCP instance
    """
    global _ollama_shell_filesystem_mcp_instance
    
    if _ollama_shell_filesystem_mcp_instance is None:
        model_to_use = default_model if default_model else "llama2"
        _ollama_shell_filesystem_mcp_instance = OllamaShellFilesystemMCP(model_to_use)
    elif default_model is not None:
        _ollama_shell_filesystem_mcp_instance.set_default_model(default_model)
    
    return _ollama_shell_filesystem_mcp_instance

def handle_filesystem_nl_command(command: str, model: Optional[str] = None) -> str:
    """
    Handle a natural language filesystem command.
    
    Args:
        command: Natural language command to execute
        model: Ollama model to use (optional, uses default model if not specified)
        
    Returns:
        Response from the LLM
    """
    # Get the Ollama Shell Filesystem MCP integration
    integration = get_ollama_shell_filesystem_mcp(model)
    
    # Handle the command
    return integration.handle_command(command, model)

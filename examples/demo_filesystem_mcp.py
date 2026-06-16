#!/usr/bin/env python3
"""
Demo script for Filesystem MCP Protocol integration with Ollama Shell

This script demonstrates how to use the Filesystem MCP Protocol integration
to interact with the filesystem using natural language.
"""

import os
import sys
import json
import logging
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("demo_filesystem_mcp")

# Import the Ollama Shell Filesystem MCP integration
try:
    from ollama_shell_filesystem_mcp import get_ollama_shell_filesystem_mcp
    FILESYSTEM_MCP_AVAILABLE = True
except ImportError:
    FILESYSTEM_MCP_AVAILABLE = False
    logger.error("Ollama Shell Filesystem MCP integration not available")

# Rich console for pretty output
console = Console()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Demo for Filesystem MCP Protocol integration with Ollama Shell")
    parser.add_argument("--api-key", type=str, help="Anthropic API key")
    parser.add_argument("--model", type=str, default="claude-3-opus-20240229", help="Anthropic model to use")
    return parser.parse_args()

def check_api_key(args):
    """Check if API key is provided or available in environment variables."""
    api_key = args.api_key
    
    # Check if API key is provided
    if not api_key:
        # Check if API key is available in environment variables
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # If API key is still not available, prompt the user
    if not api_key:
        console.print(Panel.fit(
            "[bold red]API key not provided[/bold red]\n\n"
            "Please provide your Anthropic API key using the --api-key argument "
            "or by setting the ANTHROPIC_API_KEY environment variable."
        ))
        api_key = Prompt.ask("Enter your Anthropic API key")
    
    return api_key

def run_demo(api_key, model):
    """Run the demo."""
    # Get the Ollama Shell Filesystem MCP integration
    integration = get_ollama_shell_filesystem_mcp(api_key)
    
    if not integration.available:
        console.print(Panel.fit(
            "[bold red]Filesystem MCP Protocol integration not available[/bold red]\n\n"
            "Please make sure the Filesystem MCP Protocol server is running."
        ))
        return
    
    # Display welcome message
    console.print(Panel.fit(
        "[bold green]Filesystem MCP Protocol Demo[/bold green]\n\n"
        "This demo allows you to interact with the filesystem using natural language.\n"
        "Type 'exit' or 'quit' to exit the demo."
    ))
    
    # Main loop
    while True:
        # Get user input
        command = Prompt.ask("\n[bold blue]Enter a natural language command[/bold blue]")
        
        # Check if user wants to exit
        if command.lower() in ["exit", "quit"]:
            break
        
        # Handle the command
        try:
            console.print("[bold yellow]Processing...[/bold yellow]")
            response = integration.handle_command(command, model)
            
            # Display the response
            console.print(Panel(Markdown(response), title="Response", border_style="green"))
        except Exception as e:
            logger.error(f"Error handling command: {str(e)}")
            console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", border_style="red"))
    
    # Shutdown the integration
    integration.shutdown()
    console.print("[bold green]Demo completed. Goodbye![/bold green]")

def main():
    """Main function."""
    # Check if Filesystem MCP Protocol integration is available
    if not FILESYSTEM_MCP_AVAILABLE:
        console.print(Panel.fit(
            "[bold red]Ollama Shell Filesystem MCP integration not available[/bold red]\n\n"
            "Please make sure the required dependencies are installed:\n"
            "1. Run the install_filesystem_mcp_protocol.py script\n"
            "2. Make sure the MCP Python SDK is installed"
        ))
        return
    
    # Parse command line arguments
    args = parse_args()
    
    # Check if API key is provided
    api_key = check_api_key(args)
    
    # Run the demo
    run_demo(api_key, args.model)

if __name__ == "__main__":
    main()

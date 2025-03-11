#!/usr/bin/env python3
"""
Test script for Confluence MCP integration connection.
This script tests the connection to Confluence Cloud and displays the results.
"""

import json
import logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_confluence")

# Import the Confluence MCP integration
from confluence_mcp_integration import get_confluence_mcp_integration

# Rich console for pretty output
console = Console()

def main():
    """Test the Confluence MCP integration connection."""
    console.print("[bold]Testing Confluence MCP Integration Connection[/bold]")
    
    # Get the Confluence MCP integration instance
    confluence_mcp = get_confluence_mcp_integration()
    
    # Check if the integration is configured
    if not confluence_mcp.is_configured():
        console.print(Panel(
            "Confluence MCP integration not configured. Please set CONFLUENCE_URL, "
            "CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL environment variables.",
            title="Configuration Error",
            border_style="red"
        ))
        return
        
    # Display configuration information (with masked credentials)
    console.print("[bold]Configuration:[/bold]")
    url = confluence_mcp.confluence_url
    email = confluence_mcp.email
    token = "*" * 8 if confluence_mcp.api_token else "Not set"
    
    console.print(f"URL: {url}")
    console.print(f"Email: {email}")
    console.print(f"API Token: {token}")
    
    # Display authentication headers (with masked token)
    console.print("\n[bold]Authentication Headers:[/bold]")
    headers = confluence_mcp.get_auth_headers()
    # Display the first 10 characters of the Authorization header for debugging
    auth_header = headers.get("Authorization", "")
    auth_preview = auth_header[:15] + "..." if auth_header else "Not set"
    console.print(f"Authorization: {auth_preview}")
    console.print(f"Content-Type: {headers.get('Content-Type', 'Not set')}")
    
    # Test the connection
    console.print("[bold]Testing connection to Confluence Cloud...[/bold]")
    result = confluence_mcp.test_connection()
    
    if result["status"] == "success":
        # Display success message
        console.print(Panel(
            f"[bold green]Success:[/bold green] {result['message']}",
            title="Connection Test",
            border_style="green"
        ))
        
        # Display spaces if available
        if "data" in result and "results" in result["data"]:
            spaces = result["data"]["results"]
            if spaces:
                console.print("[bold]Available Confluence Spaces:[/bold]")
                for space in spaces:
                    console.print(f"- [bold]{space.get('name', 'Unknown')}[/bold] (Key: {space.get('key', 'Unknown')})")
            else:
                console.print("[yellow]No spaces found in this Confluence instance.[/yellow]")
    else:
        # Display error message
        console.print(Panel(
            f"[bold red]Error:[/bold red] {result['message']}",
            title="Connection Test",
            border_style="red"
        ))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for Confluence API using the Atlassian Python API library.
This script tests the connection to Confluence Cloud using the atlassian-python-api library.
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Rich console for pretty output
console = Console()

# Load environment variables from the same locations as the Confluence MCP integration
created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Created Files')
config_path = os.path.join(created_files_dir, 'confluence_config.env')

# Load from the Created Files directory if it exists, otherwise try the default .env file
if os.path.exists(config_path):
    console.print(f"Loading environment from: {config_path}")
    load_dotenv(dotenv_path=config_path)
else:
    console.print("Falling back to default .env file")
    load_dotenv()  # Fallback to default .env file

def main():
    """Test connection to Confluence API using atlassian-python-api."""
    console.print("[bold]Testing Confluence API Connection using atlassian-python-api[/bold]")
    
    # Get configuration from environment variables
    confluence_url = os.environ.get("CONFLUENCE_URL")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN")
    email = os.environ.get("CONFLUENCE_EMAIL")
    
    if not confluence_url or not api_token or not email:
        console.print(Panel(
            "Confluence configuration not found. Please set CONFLUENCE_URL, "
            "CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL environment variables.",
            title="Configuration Error",
            border_style="red"
        ))
        return
    
    # Clean up URL
    confluence_url = confluence_url.rstrip('/')
    
    # Display configuration (with masked credentials)
    console.print("[bold]Configuration:[/bold]")
    console.print(f"URL: {confluence_url}")
    console.print(f"Email: {email}")
    console.print(f"API Token: {'*' * 8}")
    
    try:
        # Try to install the atlassian-python-api package if not already installed
        try:
            from atlassian import Confluence
        except ImportError:
            console.print("[yellow]Installing atlassian-python-api package...[/yellow]")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "atlassian-python-api"])
            from atlassian import Confluence
        
        # Create Confluence client
        console.print("\n[bold]Connecting to Confluence...[/bold]")
        
        # Print the original URL for debugging
        console.print(f"Original URL: {confluence_url}")
        
        # Ensure we have a valid URL format
        from urllib.parse import urlparse
        parsed_url = urlparse(confluence_url)
        
        # Make sure we have a scheme and netloc
        if not parsed_url.scheme or not parsed_url.netloc:
            console.print(Panel(
                f"Invalid URL format: {confluence_url}. Please provide a complete URL with scheme and hostname.",
                title="URL Error",
                border_style="red"
            ))
            return
        
        # For Confluence Cloud, we need the base URL without the /wiki part
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        console.print(f"Using base URL: {base_url}")
        
        # Initialize the Confluence client
        confluence = Confluence(
            url=base_url,
            username=email,
            password=api_token,
            cloud=True  # Specify that we're connecting to Confluence Cloud
        )
        
        # Test the connection by getting spaces
        console.print("[bold]Fetching spaces...[/bold]")
        spaces = confluence.get_all_spaces(limit=5)
        
        if spaces:
            console.print(Panel(
                "Successfully connected to Confluence API!",
                title="Connection Test",
                border_style="green"
            ))
            
            # Display spaces
            console.print("[bold]Available Spaces:[/bold]")
            for space in spaces.get('results', []):
                console.print(f"- {space.get('name', 'Unknown')} (Key: {space.get('key', 'Unknown')})")
        else:
            console.print(Panel(
                "Connected to Confluence API, but no spaces were found.",
                title="Connection Test",
                border_style="yellow"
            ))
            
    except Exception as e:
        console.print(Panel(
            f"Error connecting to Confluence API: {str(e)}",
            title="Connection Error",
            border_style="red"
        ))
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for Confluence Server API using Personal Access Token (PAT) authentication.
This script tests the connection to Confluence Server using PAT authentication.
"""

import os
import requests
import json
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
    """Test connection to Confluence Server API using PAT authentication."""
    console.print("[bold]Testing Confluence Server API Connection with Personal Access Token[/bold]")
    
    # Get configuration from environment variables
    confluence_url = os.environ.get("CONFLUENCE_URL")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN")  # This should be the PAT
    email = os.environ.get("CONFLUENCE_EMAIL")  # This is still needed for some API calls
    
    if not confluence_url or not api_token:
        console.print(Panel(
            "Confluence configuration not found. Please set CONFLUENCE_URL and "
            "CONFLUENCE_API_TOKEN environment variables.",
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
    console.print(f"PAT: {'*' * 8}")
    
    # Create authentication headers for PAT
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check"  # Required for some Confluence Server API calls
    }
    
    console.print("\n[bold]Authentication Headers:[/bold]")
    # Show a preview of the Authorization header
    auth_preview = headers["Authorization"][:15] + "..." if headers["Authorization"] else "Not set"
    console.print(f"Authorization: {auth_preview}")
    for key, value in headers.items():
        if key != "Authorization":
            console.print(f"{key}: {value}")
    
    # Test different API endpoints for Confluence Server
    console.print("\n[bold]Testing connection to Confluence Server with PAT...[/bold]")
    
    # List of endpoints to try for Confluence Server
    endpoints = [
        "/rest/api/space",  # Standard endpoint
        "/wiki/rest/api/space",  # With wiki prefix
        "/confluence/rest/api/space",  # With confluence prefix
        "/rest/api/content"  # Content endpoint
    ]
    
    success = False
    
    for endpoint in endpoints:
        url = f"{confluence_url}{endpoint}"
        console.print(f"Trying endpoint: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            console.print(f"Status code: {response.status_code}")
            console.print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        console.print(Panel(
                            f"Successfully connected to Confluence Server API using endpoint: {endpoint}",
                            title="Connection Test",
                            border_style="green"
                        ))
                        console.print("[bold]Response preview:[/bold]")
                        console.print(json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data, indent=2)) > 500 else json.dumps(data, indent=2))
                        success = True
                        break
                    except json.JSONDecodeError:
                        console.print(Panel(
                            f"Received invalid JSON response from endpoint: {endpoint}",
                            title="JSON Error",
                            border_style="yellow"
                        ))
                        console.print(f"Response preview: {response.text[:200]}...")
                else:
                    console.print(Panel(
                        f"Received non-JSON response from endpoint: {endpoint}",
                        title="Content Type Error",
                        border_style="yellow"
                    ))
                    console.print(f"Response preview: {response.text[:200]}...")
            else:
                console.print(Panel(
                    f"Failed to connect to endpoint {endpoint}: Status code {response.status_code}",
                    title="Connection Error",
                    border_style="red"
                ))
                console.print(f"Response preview: {response.text[:200]}...")
                
        except Exception as e:
            console.print(Panel(
                f"Error connecting to endpoint {endpoint}: {str(e)}",
                title="Connection Error",
                border_style="red"
            ))
    
    if not success:
        console.print(Panel(
            "Failed to connect to any Confluence Server API endpoint using PAT authentication. "
            "Please check your URL and Personal Access Token.",
            title="Connection Failed",
            border_style="red"
        ))
        
        # Provide troubleshooting tips
        console.print("\n[bold]Troubleshooting Tips for PAT Authentication:[/bold]")
        console.print("1. Verify that your Personal Access Token is valid and not expired")
        console.print("2. Ensure the PAT has the necessary permissions for API access")
        console.print("3. Check if the Confluence Server instance supports PAT authentication")
        console.print("4. Try accessing the Confluence web interface and generating a new PAT")
        console.print("5. Consult with your Confluence administrator about API access requirements")

if __name__ == "__main__":
    main()

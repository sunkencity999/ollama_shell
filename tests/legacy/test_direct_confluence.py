#!/usr/bin/env python3
"""
Direct test script for Confluence API connection.
This script tests the connection using direct requests to the Confluence API.
"""

import os
import json
import requests
import base64
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
    """Test direct connection to Confluence API."""
    console.print("[bold]Testing Direct Confluence API Connection[/bold]")
    
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
    
    # Try different authentication methods
    
    # Method 1: Basic Auth with email:token
    console.print("\n[bold]Method 1: Basic Auth with email:token[/bold]")
    try:
        auth_str = f"{email}:{api_token}"
        auth_bytes = auth_str.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode('ascii')
        
        headers1 = {
            "Authorization": f"Basic {base64_auth}",
            "Content-Type": "application/json"
        }
        
        url = f"{confluence_url}/wiki/rest/api/space"
        console.print(f"Testing URL: {url}")
        console.print(f"Auth header: Basic {base64_auth[:10]}...")
        
        response = requests.get(url, headers=headers1)
        
        console.print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            console.print(Panel("Successfully connected using Method 1", border_style="green"))
            spaces = response.json().get("results", [])
            if spaces:
                console.print("[bold]Available Spaces:[/bold]")
                for space in spaces[:5]:  # Show first 5 spaces
                    console.print(f"- {space.get('name', 'Unknown')} (Key: {space.get('key', 'Unknown')})")
        else:
            console.print(Panel(f"Failed with status code {response.status_code}", border_style="red"))
            console.print(f"Response: {response.text[:200]}...")
    except Exception as e:
        console.print(Panel(f"Error: {str(e)}", border_style="red"))
    
    # Method 2: Basic Auth with username:token
    console.print("\n[bold]Method 2: Basic Auth with username:token[/bold]")
    try:
        # Extract username from email
        username = email.split('@')[0]
        auth_str = f"{username}:{api_token}"
        auth_bytes = auth_str.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode('ascii')
        
        headers2 = {
            "Authorization": f"Basic {base64_auth}",
            "Content-Type": "application/json"
        }
        
        url = f"{confluence_url}/wiki/rest/api/space"
        console.print(f"Testing URL: {url}")
        console.print(f"Auth header: Basic {base64_auth[:10]}...")
        
        response = requests.get(url, headers=headers2)
        
        console.print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            console.print(Panel("Successfully connected using Method 2", border_style="green"))
            spaces = response.json().get("results", [])
            if spaces:
                console.print("[bold]Available Spaces:[/bold]")
                for space in spaces[:5]:  # Show first 5 spaces
                    console.print(f"- {space.get('name', 'Unknown')} (Key: {space.get('key', 'Unknown')})")
        else:
            console.print(Panel(f"Failed with status code {response.status_code}", border_style="red"))
            console.print(f"Response: {response.text[:200]}...")
    except Exception as e:
        console.print(Panel(f"Error: {str(e)}", border_style="red"))
    
    # Method 3: API Token as Bearer token
    console.print("\n[bold]Method 3: Bearer Token[/bold]")
    try:
        headers3 = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{confluence_url}/wiki/rest/api/space"
        console.print(f"Testing URL: {url}")
        console.print(f"Auth header: Bearer {api_token[:5]}...")
        
        response = requests.get(url, headers=headers3)
        
        console.print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            console.print(Panel("Successfully connected using Method 3", border_style="green"))
            # Debug the response content
            console.print("[bold]Response Content:[/bold]")
            console.print(f"Content type: {response.headers.get('Content-Type', 'Unknown')}")
            console.print(f"Response length: {len(response.text)}")
            console.print(f"First 100 characters: {response.text[:100]}")
            
            try:
                # Try to parse the JSON response
                json_data = response.json()
                console.print("[bold]Successfully parsed JSON response[/bold]")
                spaces = json_data.get("results", [])
                if spaces:
                    console.print("[bold]Available Spaces:[/bold]")
                    for space in spaces[:5]:  # Show first 5 spaces
                        console.print(f"- {space.get('name', 'Unknown')} (Key: {space.get('key', 'Unknown')})")
                else:
                    console.print("No spaces found in the response")
            except json.JSONDecodeError as e:
                console.print(Panel(f"Error parsing JSON: {str(e)}", border_style="red"))
                console.print("[bold]Raw response (first 500 chars):[/bold]")
                console.print(response.text[:500])
        else:
            console.print(Panel(f"Failed with status code {response.status_code}", border_style="red"))
            console.print(f"Response: {response.text[:200]}...")
    except Exception as e:
        console.print(Panel(f"Error: {str(e)}", border_style="red"))

if __name__ == "__main__":
    main()

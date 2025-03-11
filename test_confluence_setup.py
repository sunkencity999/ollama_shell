#!/usr/bin/env python3
"""
Test Confluence Integration Setup

This script helps verify that the Confluence integration is properly configured.
It checks for the existence of the configuration file, validates the settings,
and tests the connection to the Confluence instance.
"""

import os
import sys
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

console = Console()

def check_config_file():
    """Check if the Confluence configuration file exists"""
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Check for the configuration file
    config_file = os.path.join(project_root, "Created Files", "confluence_config.env")
    template_file = os.path.join(project_root, "Created Files", "config", "confluence_config_template.env")
    
    if os.path.exists(config_file):
        console.print(Panel("[green]✅ Confluence configuration file found[/green]", title="Configuration Check"))
        return config_file
    else:
        console.print(Panel("[yellow]⚠️ Confluence configuration file not found[/yellow]", title="Configuration Check"))
        
        if os.path.exists(template_file):
            console.print(f"[yellow]Template file exists at: {template_file}[/yellow]")
            console.print("[yellow]Would you like to create a configuration file from the template? (y/n)[/yellow]")
            choice = input().lower()
            
            if choice == 'y':
                # Create the config file from the template
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                with open(template_file, 'r') as src, open(config_file, 'w') as dst:
                    dst.write(src.read())
                console.print(f"[green]✅ Created configuration file at: {config_file}[/green]")
                console.print("[yellow]Please edit this file with your Confluence details before continuing.[/yellow]")
                console.print("[yellow]Would you like to continue with the test? (y/n)[/yellow]")
                choice = input().lower()
                
                if choice == 'y':
                    return config_file
                else:
                    console.print("[yellow]Exiting. Please run this script again after editing the configuration file.[/yellow]")
                    sys.exit(0)
            else:
                console.print("[yellow]Exiting. Please create a configuration file before running this script.[/yellow]")
                sys.exit(1)
        else:
            console.print("[red]❌ Template file not found. Please run the installation script first.[/red]")
            sys.exit(1)
    
    return None

def validate_config(config_file):
    """Validate the configuration settings"""
    # Load the configuration
    load_dotenv(config_file)
    
    # Check required settings
    required_settings = {
        "CONFLUENCE_URL": os.environ.get("CONFLUENCE_URL"),
        "CONFLUENCE_EMAIL": os.environ.get("CONFLUENCE_EMAIL"),
        "CONFLUENCE_API_TOKEN": os.environ.get("CONFLUENCE_API_TOKEN"),
    }
    
    # Optional settings with defaults
    auth_method = os.environ.get("CONFLUENCE_AUTH_METHOD", "pat").lower()
    is_cloud = os.environ.get("CONFLUENCE_IS_CLOUD", "false").lower() == "true"
    
    # Create a table to display the configuration
    table = Table(title="Confluence Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status", style="yellow")
    
    all_valid = True
    
    for setting, value in required_settings.items():
        if value:
            status = "[green]✅ Valid[/green]"
            display_value = value
            # Mask the API token
            if setting == "CONFLUENCE_API_TOKEN":
                display_value = value[:8] + "..." if len(value) > 8 else "********"
        else:
            status = "[red]❌ Missing[/red]"
            display_value = "[red]Not set[/red]"
            all_valid = False
        
        table.add_row(setting, display_value, status)
    
    # Add optional settings
    table.add_row("CONFLUENCE_AUTH_METHOD", auth_method, "[green]✅ Using default (pat)[/green]" if auth_method == "pat" else f"[yellow]Using {auth_method}[/yellow]")
    table.add_row("CONFLUENCE_IS_CLOUD", str(is_cloud), "[green]✅ Valid[/green]")
    
    console.print(table)
    
    if not all_valid:
        console.print(Panel("[red]❌ Configuration is incomplete. Please update your configuration file.[/red]", title="Validation Result"))
        return False
    
    console.print(Panel("[green]✅ Configuration is valid[/green]", title="Validation Result"))
    return True

def test_connection():
    """Test the connection to the Confluence instance"""
    url = os.environ.get("CONFLUENCE_URL")
    email = os.environ.get("CONFLUENCE_EMAIL")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN")
    auth_method = os.environ.get("CONFLUENCE_AUTH_METHOD", "pat").lower()
    is_cloud = os.environ.get("CONFLUENCE_IS_CLOUD", "false").lower() == "true"
    
    # Prepare headers based on authentication method
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check"
    }
    
    if auth_method == "basic":
        import base64
        auth_str = f"{email}:{api_token}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_auth}"
    elif auth_method == "bearer":
        headers["Authorization"] = f"Bearer {api_token}"
    elif auth_method == "pat":
        headers["Authorization"] = f"Bearer {api_token}"
    else:
        console.print(f"[red]❌ Unknown authentication method: {auth_method}[/red]")
        return False
    
    # Determine the API endpoint based on instance type
    if is_cloud:
        api_endpoint = f"{url}/wiki/rest/api/space"
        if not url.startswith("https://"):
            api_endpoint = f"https://{url}/wiki/rest/api/space"
    else:
        # For Server instances, the endpoint is different
        api_endpoint = f"{url}/rest/api/space"
        if not url.startswith("https://"):
            api_endpoint = f"https://{url}/rest/api/space"
    
    console.print(f"[cyan]Testing connection to: {api_endpoint}[/cyan]")
    console.print(f"[cyan]Using authentication method: {auth_method}[/cyan]")
    
    try:
        response = requests.get(api_endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            console.print(Panel(f"[green]✅ Successfully connected to Confluence API (Status: {response.status_code})[/green]", title="Connection Test"))
            
            # Display some spaces as proof of successful connection
            try:
                spaces = response.json().get("results", [])
                if spaces:
                    space_table = Table(title="Sample Confluence Spaces")
                    space_table.add_column("Name", style="cyan")
                    space_table.add_column("Key", style="green")
                    space_table.add_column("Type", style="yellow")
                    
                    for space in spaces[:5]:  # Show up to 5 spaces
                        space_table.add_row(
                            space.get("name", "Unknown"),
                            space.get("key", "Unknown"),
                            space.get("type", "Unknown")
                        )
                    
                    console.print(space_table)
                else:
                    console.print("[yellow]No spaces found or you don't have permission to view them.[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Could not parse spaces: {str(e)}[/yellow]")
            
            return True
        else:
            console.print(Panel(f"[red]❌ Failed to connect to Confluence API (Status: {response.status_code})[/red]", title="Connection Test"))
            console.print(f"[yellow]Response: {response.text}[/yellow]")
            
            if response.status_code == 401:
                console.print("[yellow]Authentication failed. Please check your credentials.[/yellow]")
            elif response.status_code == 403:
                console.print("[yellow]Permission denied. Your account may not have sufficient permissions.[/yellow]")
            elif response.status_code == 404:
                console.print("[yellow]API endpoint not found. Please check your Confluence URL and instance type (Cloud/Server).[/yellow]")
            
            return False
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"[red]❌ Connection error: {str(e)}[/red]", title="Connection Test"))
        return False

def main():
    """Main function"""
    console.print(Panel("[bold cyan]Confluence Integration Setup Test[/bold cyan]", subtitle="Ollama Shell"))
    
    # Check for configuration file
    config_file = check_config_file()
    if not config_file:
        return
    
    # Validate configuration
    if not validate_config(config_file):
        return
    
    # Test connection
    if test_connection():
        console.print(Panel("[green bold]✅ Confluence integration is properly configured and working![/green bold]", title="Final Result"))
    else:
        console.print(Panel("[red bold]❌ Confluence integration test failed. Please check the errors above.[/red bold]", title="Final Result"))

if __name__ == "__main__":
    main()

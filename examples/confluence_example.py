#!/usr/bin/env python3
"""
Confluence Integration Example

This script demonstrates how to use the Confluence integration in Ollama Shell
programmatically. It shows how to connect to Confluence, list spaces, create pages,
and search for content.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the Confluence integration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Confluence integration
from confluence_mcp_integration import ConfluenceMCPIntegration

def load_config():
    """Load the Confluence configuration from the environment file"""
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load the configuration file
    config_file = os.path.join(project_root, "Created Files", "confluence_config.env")
    
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        print("Please run the installation script or create the configuration file manually.")
        sys.exit(1)
    
    # Load the configuration
    load_dotenv(config_file)
    
    # Check required settings
    required_vars = ["CONFLUENCE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please update your configuration file.")
        sys.exit(1)
    
    return {
        "url": os.environ.get("CONFLUENCE_URL"),
        "email": os.environ.get("CONFLUENCE_EMAIL"),
        "api_token": os.environ.get("CONFLUENCE_API_TOKEN"),
        "auth_method": os.environ.get("CONFLUENCE_AUTH_METHOD", "pat"),
        "is_cloud": os.environ.get("CONFLUENCE_IS_CLOUD", "false").lower() == "true"
    }

def print_section(title):
    """Print a section title"""
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)

def main():
    """Main function"""
    print_section("Confluence Integration Example")
    
    # Load the configuration
    config = load_config()
    print(f"✅ Configuration loaded from environment file")
    print(f"📌 Connecting to: {config['url']}")
    print(f"📌 Authentication method: {config['auth_method']}")
    print(f"📌 Instance type: {'Cloud' if config['is_cloud'] else 'Server'}")
    
    # Initialize the Confluence integration
    confluence = ConfluenceMCPIntegration(
        confluence_url=config['url'],
        api_token=config['api_token']
    )
    
    # Test the connection
    print_section("Testing Connection")
    try:
        result = confluence.test_connection()
        print(f"✅ Connection successful: {result}")
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        sys.exit(1)
    
    # List spaces
    print_section("Listing Spaces")
    try:
        spaces = confluence.list_spaces()
        print(f"✅ Found {len(spaces)} spaces")
        
        # Print the first 5 spaces
        for i, space in enumerate(spaces[:5]):
            print(f"{i+1}. {space['name']} (Key: {space['key']})")
        
        if len(spaces) > 5:
            print(f"... and {len(spaces) - 5} more")
        
        # Select a space for further operations
        if spaces:
            selected_space = spaces[0]
            print(f"\n📌 Selected space: {selected_space['name']} (Key: {selected_space['key']})")
        else:
            print("❌ No spaces found. Cannot continue with examples.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to list spaces: {str(e)}")
        sys.exit(1)
    
    # List pages in the selected space
    print_section(f"Listing Pages in {selected_space['name']}")
    try:
        pages = confluence.list_pages(selected_space['key'])
        print(f"✅ Found {len(pages)} pages")
        
        # Print the first 5 pages
        for i, page in enumerate(pages[:5]):
            print(f"{i+1}. {page['title']} (ID: {page['id']})")
        
        if len(pages) > 5:
            print(f"... and {len(pages) - 5} more")
        
        # Select a page for further operations
        if pages:
            selected_page = pages[0]
            print(f"\n📌 Selected page: {selected_page['title']} (ID: {selected_page['id']})")
        else:
            print("⚠️ No pages found in this space.")
            selected_page = None
    except Exception as e:
        print(f"❌ Failed to list pages: {str(e)}")
        selected_page = None
    
    # Search for content
    print_section("Searching for Content")
    search_term = "documentation"
    try:
        results = confluence.search(search_term)
        print(f"✅ Found {len(results)} results for '{search_term}'")
        
        # Print the first 5 results
        for i, result in enumerate(results[:5]):
            print(f"{i+1}. {result['title']} (Space: {result['space']['name']})")
        
        if len(results) > 5:
            print(f"... and {len(results) - 5} more")
    except Exception as e:
        print(f"❌ Failed to search for content: {str(e)}")
    
    # Create a new page (commented out to prevent accidental page creation)
    """
    print_section("Creating a New Page")
    try:
        page_title = "Example Page from API"
        page_content = "<p>This page was created using the Confluence API.</p>"
        
        new_page = confluence.create_page(
            space_key=selected_space['key'],
            title=page_title,
            body=page_content
        )
        
        print(f"✅ Page created: {page_title} (ID: {new_page['id']})")
        print(f"📌 View the page at: {config['url']}/pages/viewpage.action?pageId={new_page['id']}")
    except Exception as e:
        print(f"❌ Failed to create page: {str(e)}")
    """
    
    print_section("Example Complete")
    print("✅ Successfully demonstrated the Confluence integration")
    print("📚 For more information, refer to the documentation in README.md")

if __name__ == "__main__":
    main()

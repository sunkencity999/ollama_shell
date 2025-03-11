#!/usr/bin/env python3
"""
Ollama Shell Confluence MCP Integration

This module provides the interface between Ollama Shell and the Confluence MCP integration,
allowing users to interact with Confluence Cloud through natural language commands.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ollama_shell_confluence")

# Import the Confluence MCP integration
try:
    from confluence_mcp_integration import get_confluence_mcp_integration
    CONFLUENCE_MCP_AVAILABLE = True
except ImportError:
    CONFLUENCE_MCP_AVAILABLE = False
    logger.warning("Confluence MCP integration not available. Please install the required dependencies.")

# Rich console for pretty output
console = Console()

def get_ollama_shell_confluence_mcp():
    """
    Get the Confluence MCP integration instance.
    
    Returns:
        The Confluence MCP integration instance or None if not available
    """
    if not CONFLUENCE_MCP_AVAILABLE:
        return None
    
    return get_confluence_mcp_integration()

def handle_confluence_nl_command(command: str, model: str = "llama3") -> Dict[str, Any]:
    """
    Handle a natural language command related to Confluence.
    
    Args:
        command: The natural language command to execute
        model: The Ollama model to use for processing the command
        
    Returns:
        The result of the command execution
    """
    if not CONFLUENCE_MCP_AVAILABLE:
        return {
            "error": "Confluence MCP integration not available. Please install the required dependencies."
        }
    
    confluence_mcp = get_confluence_mcp_integration()
    
    if not confluence_mcp.is_configured():
        return {
            "error": "Confluence MCP integration not configured. Please set CONFLUENCE_URL, "
                     "CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL environment variables "
                     "or configure them in the Settings menu."
        }
    
    try:
        # Execute the command and get the result
        result = confluence_mcp.execute_natural_language_command(command, model=model)
        
        # Debug logging
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result content: {result}")
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            logger.warning(f"Result is not a dictionary, converting: {result}")
            return {"message": {"content": str(result)}}
        
        # Check if the result has a message key with content
        if "message" in result and "content" in result["message"]:
            # Try to parse the content as JSON if it's a string that looks like JSON
            content = result["message"]["content"]
            if isinstance(content, str) and content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    # Try to parse the content as JSON
                    import json
                    json_content = json.loads(content)
                    
                    # Check if it's a tool call format
                    if "name" in json_content and "parameters" in json_content:
                        # Extract the function name and parameters
                        function_name = json_content["name"]
                        parameters = json_content["parameters"]
                        
                        logger.info(f"Detected function call in content: {function_name} with parameters: {parameters}")
                        
                        # Call the function directly
                        if function_name == "search_confluence_pages" and hasattr(confluence_mcp, function_name):
                            # Convert parameters to the correct types if needed
                            if "limit" in parameters and isinstance(parameters["limit"], str):
                                parameters["limit"] = int(parameters["limit"])
                                
                            # Call the function
                            return getattr(confluence_mcp, function_name)(**parameters)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse content as JSON: {content}")
            
            # If we couldn't parse as JSON or execute a function, return as is
            return result
        
        # Check if there's an error key
        if "error" in result:
            return {"error": result["error"]}
            
        # If we get here, we need to convert the result to a proper structure
        return {"message": {"content": str(result)}}
    except Exception as e:
        logger.error(f"Error executing Confluence natural language command: {str(e)}")
        return {"error": str(e)}

def display_confluence_result(result: Dict[str, Any]) -> None:
    """
    Display the result of a Confluence command in a rich format.
    
    Args:
        result: The result of the command execution
    """
    # Log the result for debugging
    logger.info(f"Result type: {type(result)}")
    
    if not isinstance(result, dict):
        console.print(Panel(f"Unexpected result type: {type(result)}", 
                           title="Confluence Error", 
                           border_style="red"))
        return
        
    logger.info(f"Result keys: {result.keys()}")
    
    # Check for error
    if "error" in result:
        console.print(Panel(f"[bold red]Error:[/bold red] {result['error']}", 
                           title="Confluence Error", 
                           border_style="red"))
        return
        
    # Handle case where search results are wrapped in a message content field as a string
    if "message" in result and "content" in result["message"] and isinstance(result["message"]["content"], str):
        content_str = result["message"]["content"]
        # Check if the content looks like a dictionary with search results
        if "'search_query'" in content_str and "'results'" in content_str:
            try:
                # Try to safely evaluate the string as a Python literal
                import ast
                search_result = ast.literal_eval(content_str)
                if isinstance(search_result, dict) and "search_query" in search_result and "results" in search_result:
                    # We found search results in the message content, use this instead
                    result = search_result
            except (SyntaxError, ValueError) as e:
                logger.warning(f"Failed to parse message content as search results: {e}")
    
    # Check for search results
    if "search_query" in result and "results" in result:
        # This is a search result
        search_query = result["search_query"]
        total_results = result.get("total_results", len(result["results"]))
        search_results = result["results"]
        
        if search_results and len(search_results) > 0:
            # Format the search results
            content = f"### Search Results for: '{search_query}'"
            content += f"\n\nFound {total_results} results:\n\n"
            
            # Group results by type for better organization
            pages = []
            attachments = []
            others = []
            
            for page in search_results:
                if page['type'].lower() == 'page':
                    pages.append(page)
                elif page['type'].lower() == 'attachment':
                    attachments.append(page)
                else:
                    others.append(page)
            
            # Display LLM analysis if available
            if "analysis" in result and result["analysis"]:
                content += "### Analysis\n\n"
                content += result["analysis"]
                content += "\n\n---\n\n"
            
            # Display pages first (most relevant)
            if pages:
                content += "#### Pages\n\n"
                for i, page in enumerate(pages, 1):
                    # Format title as clickable link with proper URL formatting
                    page_url = page['url']
                    # Ensure URL is properly formatted
                    if not page_url.startswith(('http://', 'https://')):
                        # If it's a relative URL, make it absolute
                        if page_url.startswith('/'):
                            confluence_url = os.environ.get("CONFLUENCE_URL", "").rstrip('/')
                            page_url = f"{confluence_url}{page_url}"
                    
                    # Format as clickable link
                    content += f"**{i}. [{page['title']}]({page_url})**\n"
                    # Add direct URL for easy copying
                    content += f"   - URL: {page_url}\n"
                    
                    if 'space' in page and page['space'] != 'Unknown Space':
                        content += f"   - Space: {page['space']}\n"
                    # Add excerpt if available
                    if 'excerpt' in page and page['excerpt']:
                        # Truncate excerpt if too long for display
                        excerpt = page['excerpt'][:250] + '...' if len(page['excerpt']) > 250 else page['excerpt']
                        content += f"   - *Excerpt:* {excerpt}\n"
                    content += "\n"
            
            # Display attachments
            if attachments:
                content += "#### Attachments\n\n"
                for i, page in enumerate(attachments, 1):
                    # Format title as clickable link with proper URL formatting
                    page_url = page['url']
                    # Ensure URL is properly formatted
                    if not page_url.startswith(('http://', 'https://')):
                        # If it's a relative URL, make it absolute
                        if page_url.startswith('/'):
                            confluence_url = os.environ.get("CONFLUENCE_URL", "").rstrip('/')
                            page_url = f"{confluence_url}{page_url}"
                    
                    # Format as clickable link
                    content += f"**{i}. [{page['title']}]({page_url})**\n"
                    # Add direct URL for easy copying
                    content += f"   - URL: {page_url}\n"
                    
                    if 'space' in page and page['space'] != 'Unknown Space':
                        content += f"   - Space: {page['space']}\n"
                    content += "\n"
            
            # Display other content types
            if others:
                content += "#### Other Content\n\n"
                for i, page in enumerate(others, 1):
                    # Format title as clickable link with proper URL formatting
                    page_url = page['url']
                    # Ensure URL is properly formatted
                    if not page_url.startswith(('http://', 'https://')):
                        # If it's a relative URL, make it absolute
                        if page_url.startswith('/'):
                            confluence_url = os.environ.get("CONFLUENCE_URL", "").rstrip('/')
                            page_url = f"{confluence_url}{page_url}"
                    
                    # Format as clickable link
                    content += f"**{i}. [{page['title']}]({page_url})**\n"
                    # Add direct URL for easy copying
                    content += f"   - URL: {page_url}\n"
                    content += f"   - Type: {page['type']}\n"
                    
                    if 'space' in page and page['space'] != 'Unknown Space':
                        content += f"   - Space: {page['space']}\n"
                    content += "\n"
            
            console.print(Panel(Markdown(content), 
                               title="Confluence Search Results", 
                               border_style="blue"))
        else:
            console.print(Panel(f"No results found for search query: '{search_query}'", 
                               title="Confluence Search Results", 
                               border_style="yellow"))
        return
    
    # Check for message content
    if "message" in result and isinstance(result["message"], dict) and "content" in result["message"]:
        content = result["message"]["content"]
        # Check if content is empty
        if not content or (isinstance(content, str) and not content.strip()):
            console.print(Panel("No content returned from Confluence. This could indicate that the model didn't generate a response or there was an issue with the command.", 
                               title="Confluence Result", 
                               border_style="yellow"))
        else:
            console.print(Panel(Markdown(str(content)), 
                               title="Confluence Result", 
                               border_style="blue"))
    elif "message" in result:
        # Handle case where message exists but doesn't have content
        console.print(Panel(str(result["message"]), 
                           title="Confluence Result", 
                           border_style="blue"))
    else:
        # Fallback for unexpected structure - just display the raw result
        console.print(Panel(str(result), 
                           title="Confluence Raw Result", 
                           border_style="yellow"))

def check_confluence_configuration():
    """
    Check if the Confluence MCP integration is properly configured.
    
    Returns:
        A tuple of (is_configured, message)
    """
    if not CONFLUENCE_MCP_AVAILABLE:
        return False, "Confluence MCP integration not available. Please install the required dependencies."
    
    confluence_mcp = get_confluence_mcp_integration()
    
    if not confluence_mcp.is_configured():
        return False, "Confluence MCP integration not configured. Please set CONFLUENCE_URL, " \
                     "CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL environment variables " \
                     "or configure them in the Settings menu."
    
    return True, "Confluence MCP integration is properly configured."

def save_confluence_config(url: str, token: str, email: str) -> bool:
    """
    Save the Confluence configuration to the .env file.
    
    Args:
        url: The Confluence Cloud URL
        token: The Confluence API token
        email: The Confluence user email
        
    Returns:
        True if the configuration was saved successfully, False otherwise
    """
    try:
        # Store configuration in the Created Files directory
        created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Created Files')
        
        # Ensure the Created Files directory exists
        os.makedirs(created_files_dir, exist_ok=True)
        
        # Path to the configuration file
        env_path = os.path.join(created_files_dir, 'confluence_config.env')
        
        # Read existing content if file exists
        env_content = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        env_content[key] = value
        
        # Update with new values
        env_content['CONFLUENCE_URL'] = url
        env_content['CONFLUENCE_API_TOKEN'] = token
        env_content['CONFLUENCE_EMAIL'] = email
        
        # Write back to file
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        # Update the integration instance with new values
        if CONFLUENCE_MCP_AVAILABLE:
            confluence_mcp = get_confluence_mcp_integration()
            confluence_mcp.confluence_url = url
            confluence_mcp.api_token = token
            confluence_mcp.email = email
        
        return True
    except Exception as e:
        logger.error(f"Error saving Confluence configuration: {str(e)}")
        return False

#!/usr/bin/env python3
"""
Confluence MCP Integration for Ollama Shell

This module integrates the Model Context Protocol (MCP) Confluence server
with Ollama Shell, allowing LLMs to interact with Confluence Cloud through
natural language.
"""

import os
import sys
import json
import logging
import subprocess
import threading
import time
import requests
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("confluence_mcp")

# Load environment variables
# First try to load from the Created Files directory
created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Created Files')
config_path = os.path.join(created_files_dir, 'confluence_config.env')

# Load from the Created Files directory if it exists, otherwise try the default .env file
if os.path.exists(config_path):
    load_dotenv(dotenv_path=config_path)
else:
    load_dotenv()  # Fallback to default .env file

class ConfluenceMCPIntegration:
    """
    Confluence MCP Integration for Ollama Shell.
    
    This class provides methods to interact with Confluence Cloud through
    the Model Context Protocol (MCP).
    """
    
    def __init__(self, confluence_url=None, api_token=None):
        """
        Initialize the Confluence MCP Integration.
        
        Args:
            confluence_url: The URL of your Confluence Cloud instance
            api_token: Your Confluence API token or Personal Access Token (PAT)
        """
        self.confluence_url = confluence_url or os.environ.get("CONFLUENCE_URL")
        self.api_token = api_token or os.environ.get("CONFLUENCE_API_TOKEN")
        self.email = os.environ.get("CONFLUENCE_EMAIL")
        
        # Set authentication method - default to PAT for Server instances
        self.auth_method = os.environ.get("CONFLUENCE_AUTH_METHOD", "pat").lower()
        self.is_cloud = os.environ.get("CONFLUENCE_IS_CLOUD", "false").lower() == "true"
        
        # Clean up the URL if it exists to avoid double slashes
        if self.confluence_url:
            self.confluence_url = self.confluence_url.rstrip('/')
            logger.info(f"Using Confluence URL: {self.confluence_url}")
        
        # Log authentication configuration
        logger.info(f"Authentication Method: {self.auth_method}")
        logger.info(f"Instance Type: {'Cloud' if self.is_cloud else 'Server'}")
        
        # Check if required environment variables are set
        if not self.confluence_url or not self.api_token or not self.email:
            logger.warning("Confluence MCP integration not fully configured. "
                          "Please set CONFLUENCE_URL, CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL "
                          "environment variables or provide them during initialization.")
        
        # MCP tool definitions
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_confluence_spaces",
                    "description": "List all spaces in Confluence",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_confluence_space",
                    "description": "Get details about a specific space",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "The key of the space to retrieve"
                            }
                        },
                        "required": ["space_key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_confluence_pages",
                    "description": "List pages in a space",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "The key of the space to list pages from"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of pages to return (default: 25)"
                            }
                        },
                        "required": ["space_key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_confluence_page",
                    "description": "Get a specific page with its content (includes Markdown conversion)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "The ID of the page to retrieve"
                            }
                        },
                        "required": ["page_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_confluence_page",
                    "description": "Create a new page in a space",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "The key of the space to create the page in"
                            },
                            "title": {
                                "type": "string",
                                "description": "The title of the new page"
                            },
                            "content": {
                                "type": "string",
                                "description": "The content of the page in Markdown format"
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Optional ID of the parent page"
                            }
                        },
                        "required": ["space_key", "title", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_confluence_page",
                    "description": "Update an existing page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "The ID of the page to update"
                            },
                            "title": {
                                "type": "string",
                                "description": "The new title of the page"
                            },
                            "content": {
                                "type": "string",
                                "description": "The new content of the page in Markdown format"
                            },
                            "version": {
                                "type": "integer",
                                "description": "The version number to update (will be incremented)"
                            }
                        },
                        "required": ["page_id", "title", "content", "version"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_confluence_pages",
                    "description": "Search Confluence content using CQL and optionally analyze results with LLM",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cql": {
                                "type": "string",
                                "description": "Confluence Query Language (CQL) search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)"
                            },
                            "analyze_results": {
                                "type": "boolean",
                                "description": "Whether to analyze search results with LLM to provide a direct answer (default: true)"
                            }
                        },
                        "required": ["cql"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_confluence_labels",
                    "description": "Get labels for a page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "The ID of the page to get labels for"
                            }
                        },
                        "required": ["page_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_confluence_label",
                    "description": "Add a label to a page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "The ID of the page to add a label to"
                            },
                            "label": {
                                "type": "string",
                                "description": "The label to add"
                            }
                        },
                        "required": ["page_id", "label"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_confluence_label",
                    "description": "Remove a label from a page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "The ID of the page to remove a label from"
                            },
                            "label": {
                                "type": "string",
                                "description": "The label to remove"
                            }
                        },
                        "required": ["page_id", "label"]
                    }
                }
            }
        ]
    
    def is_configured(self) -> bool:
        """Check if the Confluence integration is properly configured."""
        return bool(self.confluence_url and self.api_token and self.email)
        
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Confluence Cloud.
        
        Returns:
            dict: A dictionary with status and message keys
        """
        if not self.is_configured():
            return {
                "status": "error",
                "message": "Confluence MCP integration not configured. Please set CONFLUENCE_URL, "
                          "CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL environment variables."
            }
            
        try:
            # Log the configuration (with masked credentials)
            masked_token = "*" * 8 if self.api_token else "Not set"
            logger.info(f"Testing connection with URL: {self.confluence_url}")
            logger.info(f"Email: {self.email}")
            logger.info(f"API Token: {masked_token}")
            
            # Try to list spaces as a simple test
            headers = self.get_auth_headers()
            
            # Log the headers (with masked authorization)
            auth_header = headers.get("Authorization", "")
            auth_preview = auth_header[:15] + "..." if auth_header else "Not set"
            logger.info(f"Authorization header: {auth_preview}")
            
            # Use the endpoint that worked in our testing
            url = f"{self.confluence_url}/rest/api/space"
            
            logger.info(f"Testing connection to Confluence API: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Check if the response is actually JSON
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    try:
                        return {
                            "status": "success",
                            "message": "Successfully connected to Confluence API",
                            "data": response.json()
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON response: {str(e)}")
                        return {
                            "status": "error",
                            "message": f"Error parsing JSON response: {str(e)}"
                        }
                else:
                    # If we got a 200 but not JSON, it might be a login page
                    logger.error(f"Received non-JSON response with status 200. Content-Type: {content_type}")
                    return {
                        "status": "error",
                        "message": f"Authentication failed. Received HTML login page instead of JSON data."
                    }
            else:
                # Provide more detailed error messages for common HTTP status codes
                error_message = f"Failed to connect to Confluence API: {response.status_code}"
                
                if response.status_code == 401:
                    error_message = "Authentication failed. Please check your API token and email address."
                    logger.error(f"Authentication failed with status code 401. Response: {response.text[:200]}")
                elif response.status_code == 403:
                    error_message = "Authorization failed. Your API token does not have permission to access this resource."
                    logger.error(f"Authorization failed with status code 403. Response: {response.text[:200]}")
                elif response.status_code == 404:
                    error_message = "Resource not found. Please check the Confluence URL."
                    logger.error(f"Resource not found with status code 404. Response: {response.text[:200]}")
                
                return {
                    "status": "error",
                    "message": error_message
                }
                
        except Exception as e:
            logger.error(f"Error testing Confluence connection: {str(e)}")
            return {
                "status": "error",
                "message": f"Error connecting to Confluence API: {str(e)}"
            }
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get the authentication headers for Confluence API requests.
        
        Returns:
            Dict[str, str]: Headers for Confluence API requests
        """
        import base64
        
        # Standard headers for all requests
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add authentication headers based on the configured method
        if self.auth_method == "basic":
            # Basic authentication (username/email and password/token)
            auth_str = f"{self.email}:{self.api_token}"
            auth_bytes = auth_str.encode('ascii')
            base64_bytes = base64.b64encode(auth_bytes)
            base64_auth = base64_bytes.decode('ascii')
            headers["Authorization"] = f"Basic {base64_auth}"
            
        elif self.auth_method == "bearer":
            # Bearer token authentication (typically for Cloud)
            headers["Authorization"] = f"Bearer {self.api_token}"
            
        elif self.auth_method == "pat":
            # Personal Access Token (PAT) for Server
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        # Add X-Atlassian-Token header for Server instances
        # This is required for some Confluence Server API calls, especially for attachments
        if not self.is_cloud:
            headers["X-Atlassian-Token"] = "no-check"
        
        return headers
    
    def _handle_tool_calls(self, tool_calls):
        """Handle tool calls from the model."""
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name", "")
            
            # Safely parse function arguments
            try:
                function_args_str = tool_call.get("function", {}).get("arguments", "{}")
                function_args = json.loads(function_args_str)
            except json.JSONDecodeError as json_error:
                logger.error(f"Error parsing function arguments: {str(json_error)}")
                function_args = {}
            
            try:
                if function_name == "list_confluence_spaces":
                    result = self._list_spaces()
                elif function_name == "get_confluence_space":
                    result = self._get_space(function_args.get("space_key"))
                elif function_name == "list_confluence_pages":
                    result = self._list_pages(
                        function_args.get("space_key"),
                        function_args.get("limit", 25)
                    )
                elif function_name == "get_confluence_page":
                    result = self._get_page(function_args.get("page_id"))
                elif function_name == "create_confluence_page":
                    result = self._create_page(
                        function_args.get("space_key"),
                        function_args.get("title"),
                        function_args.get("content"),
                        function_args.get("parent_id")
                    )
                elif function_name == "update_confluence_page":
                    result = self._update_page(
                        function_args.get("page_id"),
                        function_args.get("title"),
                        function_args.get("content"),
                        function_args.get("version")
                    )
                elif function_name == "search_confluence_pages":
                    result = self._search_pages(
                        function_args.get("cql"),
                        function_args.get("limit", 10)
                    )
                elif function_name == "get_confluence_labels":
                    result = self._get_labels(function_args.get("page_id"))
                elif function_name == "add_confluence_label":
                    result = self._add_label(
                        function_args.get("page_id"),
                        function_args.get("label")
                    )
                elif function_name == "remove_confluence_label":
                    result = self._remove_label(
                        function_args.get("page_id"),
                        function_args.get("label")
                    )
                else:
                    result = {"error": f"Unknown function: {function_name}"}
                
                # Ensure result is properly serialized
                try:
                    # First try to serialize the result
                    serialized_result = json.dumps(result)
                    results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "content": serialized_result
                    })
                except (TypeError, ValueError) as json_error:
                    # If serialization fails, convert to string representation
                    logger.warning(f"JSON serialization error: {str(json_error)}. Converting to string.")
                    results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "content": json.dumps({"result": str(result)})
                    })
            except Exception as e:
                logger.error(f"Error executing {function_name}: {str(e)}")
                # Handle error serialization
                try:
                    results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "content": json.dumps({"error": str(e)})
                    })
                except (TypeError, ValueError) as json_error:
                    # Fallback for serialization errors
                    logger.warning(f"JSON serialization error in error handling: {str(json_error)}")
                    results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "content": json.dumps({"error": "Error processing request"})
                    })
        
        return results
    
    def execute_natural_language_command(self, command, model="llama3"):
        """This is a complete rewrite of the function to fix JSON serialization issues"""
        """
        Execute a natural language command related to Confluence.
        
        Args:
            command: The natural language command to execute
            model: The Ollama model to use for processing the command
            
        Returns:
            The result of the command execution
        """
        if not self.is_configured():
            return {
                "message": {
                    "content": "Confluence MCP integration not configured. Please set CONFLUENCE_URL, "
                            "CONFLUENCE_API_TOKEN, and CONFLUENCE_EMAIL environment variables."
                }
            }
        
        try:
            # Prepare the system message with tool definitions
            system_message = {
                "role": "system",
                "content": (
                    "You are a helpful assistant that can interact with Confluence Cloud. "
                    "Use the provided tools to help users manage their Confluence spaces, "
                    "pages, and content. Always respond with clear, concise information "
                    "about what actions you've taken and what you've found.\n\n"
                    "When using the search_confluence_pages tool:\n"
                    "1. For natural language questions like 'How do I update SSL certificates?' or 'What is Polarion?', "
                    "extract the key terms (e.g., 'SSL certificates', 'Polarion') and use them as the search query.\n"
                    "2. Do NOT use CQL syntax like 'status:OPEN' or 'type:Page' unless the user explicitly asks for it.\n"
                    "3. For questions about specific topics, include all relevant terms in the search query.\n"
                    "4. When searching for information about procedures or how-to guides, include terms like 'guide', 'procedure', 'steps', or 'how to' in your search.\n"
                    "5. Always prioritize specific technical terms from the user's question in your search query.\n"
                    "6. The search results will now be automatically analyzed to provide a direct answer to the user's query. "
                    "This analysis will extract relevant information from the search results and present it as a concise answer.\n"
                    "7. You can control whether to analyze results by setting the 'analyze_results' parameter to true or false. "
                    "By default, analysis is enabled."
                )
            }
            
            # Prepare the user message
            user_message = {
                "role": "user",
                "content": command
            }
            
            # Create the request payload
            request_payload = {
                "model": model,
                "messages": [system_message, user_message],
                "tools": self.tools,
                "stream": False
            }
            
            logger.info(f"Making API call to Ollama with model: {model}")
            
            # Make the API call to Ollama
            try:
                response = requests.post(
                    "http://localhost:11434/api/chat",
                    json=request_payload
                )
                
                if response.status_code != 200:
                    return {
                        "message": {
                            "content": f"Ollama API error: {response.text}"
                        }
                    }
                
                # Parse the response
                result = response.json()
                logger.info(f"Raw Ollama API response: {json.dumps(result, indent=2)}")
                
                # Extract the message content
                if "message" in result:
                    message = result["message"]
                    
                    # Check for tool_calls in the message
                    if isinstance(message, dict) and "tool_calls" in message and message["tool_calls"]:
                        logger.info(f"Detected tool_calls in message: {message['tool_calls']}")
                        
                        # Process each tool call
                        for tool_call in message["tool_calls"]:
                            if "function" in tool_call:
                                function_info = tool_call["function"]
                                function_name = function_info.get("name")
                                function_args = function_info.get("arguments", {})
                                
                                # Convert arguments from string to dict if needed
                                if isinstance(function_args, str):
                                    try:
                                        function_args = json.loads(function_args)
                                    except json.JSONDecodeError:
                                        function_args = {}
                                
                                logger.info(f"Processing function call: {function_name} with args: {function_args}")
                                
                                # Execute the appropriate function based on the function name
                                if function_name == "search_confluence_pages":
                                    cql = function_args.get("cql", "")
                                    limit = int(function_args.get("limit", 10))
                                    analyze_results = function_args.get("analyze_results", True)
                                    logger.info(f"Executing search_confluence_pages with CQL: {cql}, limit: {limit}, analyze_results: {analyze_results}")
                                    return self._search_pages(cql, limit, analyze_results)
                                elif function_name == "list_confluence_spaces":
                                    return self._list_spaces()
                                elif function_name == "get_confluence_space":
                                    return self._get_space(function_args.get("space_key"))
                                elif function_name == "list_confluence_pages":
                                    return self._list_pages(
                                        function_args.get("space_key"),
                                        int(function_args.get("limit", 25))
                                    )
                                elif function_name == "get_confluence_page":
                                    return self._get_page(function_args.get("page_id"))
                                else:
                                    logger.warning(f"Unknown function in tool call: {function_name}")
                    
                    # Check if there's content in the message
                    if "content" in message:
                        content = message["content"]
                        
                        # Check if the content is a JSON string containing a tool call
                        if content:
                            try:
                                # Try to parse the content as JSON
                                content_json = json.loads(content)
                                
                                # Check if it's a tool call format
                                if isinstance(content_json, dict) and "name" in content_json and "parameters" in content_json:
                                    logger.info(f"Detected tool call in message content: {content_json}")
                                    
                                    # Extract function name and arguments
                                    function_name = content_json.get("name")
                                    function_args = content_json.get("parameters", {})
                                    
                                    # Execute the appropriate function based on the function name
                                    if function_name == "search_confluence_pages":
                                        cql = function_args.get("cql", "")
                                        limit = int(function_args.get("limit", 10))
                                        analyze_results = function_args.get("analyze_results", True)
                                        logger.info(f"Executing search_confluence_pages with CQL: {cql}, limit: {limit}, analyze_results: {analyze_results}")
                                        return self._search_pages(cql, limit, analyze_results)
                                    elif function_name == "list_confluence_spaces":
                                        return self._list_spaces()
                                    elif function_name == "get_confluence_space":
                                        return self._get_space(function_args.get("space_key"))
                                    elif function_name == "list_confluence_pages":
                                        return self._list_pages(
                                            function_args.get("space_key"),
                                            int(function_args.get("limit", 25))
                                        )
                                    elif function_name == "get_confluence_page":
                                        return self._get_page(function_args.get("page_id"))
                                    else:
                                        logger.warning(f"Unknown function in tool call: {function_name}")
                            except json.JSONDecodeError:
                                # Not JSON, continue with normal processing
                                logger.info("Message content is not JSON, continuing with normal processing")
                                pass
                            except Exception as e:
                                logger.error(f"Error processing potential tool call in message content: {str(e)}")
                                pass
                        
                        # If we get here, either the content wasn't JSON or wasn't a valid tool call
                        return {
                            "message": {
                                "content": content
                            }
                        }
                    
                    # If we get here, there was no content in the message
                    return {
                        "message": {
                            "content": str(message)
                        }
                    }
                
                # Fallback for unexpected response structure
                return {
                    "message": {
                        "content": f"Unexpected response structure: {str(result)}"
                    }
                }
                
                # Fallback for unexpected response structure
                return {
                    "message": {
                        "content": f"Received response from Confluence: {str(result)}"
                    }
                }
                
            except requests.RequestException as e:
                return {
                    "message": {
                        "content": f"Error connecting to Ollama API: {str(e)}"
                    }
                }
            except json.JSONDecodeError as e:
                return {
                    "message": {
                        "content": f"Error parsing Ollama API response: {str(e)}"
                    }
                }
            
        except Exception as e:
            logger.error(f"Error executing natural language command: {str(e)}")
            return {
                "message": {
                    "content": f"Error: {str(e)}"
                }
            }
    
    def _process_tool_calls(self, tool_calls, system_message, user_message, model):
        """
        Process tool calls and return a formatted response.
        
        Args:
            tool_calls: List of tool calls from the model
            system_message: The system message
            user_message: The user message
            model: The model to use for the final response
            
        Returns:
            A formatted response dictionary
        """
        try:
            # Handle the tool calls
            tool_results = []
            
            for tool_call in tool_calls:
                function_name = tool_call.get("function", {}).get("name", "")
                
                # Safely parse function arguments
                try:
                    function_args_str = tool_call.get("function", {}).get("arguments", "{}")
                    function_args = json.loads(function_args_str)
                except json.JSONDecodeError:
                    function_args = {}
                
                try:
                    # Execute the appropriate function based on the function name
                    if function_name == "list_confluence_spaces":
                        result = self._list_spaces()
                    elif function_name == "get_confluence_space":
                        result = self._get_space(function_args.get("space_key"))
                    elif function_name == "list_confluence_pages":
                        result = self._list_pages(
                            function_args.get("space_key"),
                            function_args.get("limit", 25)
                        )
                    elif function_name == "get_confluence_page":
                        result = self._get_page(function_args.get("page_id"))
                    elif function_name == "create_confluence_page":
                        result = self._create_page(
                            function_args.get("space_key"),
                            function_args.get("title"),
                            function_args.get("content"),
                            function_args.get("parent_id")
                        )
                    elif function_name == "update_confluence_page":
                        result = self._update_page(
                            function_args.get("page_id"),
                            function_args.get("title"),
                            function_args.get("content"),
                            function_args.get("version")
                        )
                    elif function_name == "search_confluence_pages":
                        result = self._search_pages(
                            function_args.get("cql"),
                            function_args.get("limit", 10)
                        )
                    elif function_name == "get_confluence_labels":
                        result = self._get_labels(function_args.get("page_id"))
                    elif function_name == "add_confluence_label":
                        result = self._add_label(
                            function_args.get("page_id"),
                            function_args.get("label")
                        )
                    elif function_name == "remove_confluence_label":
                        result = self._remove_label(
                            function_args.get("page_id"),
                            function_args.get("label")
                        )
                    else:
                        result = {"error": f"Unknown function: {function_name}"}
                    
                    # Ensure result is properly serialized as a string
                    result_str = json.dumps(result)
                    
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "content": result_str
                    })
                except Exception as e:
                    logger.error(f"Error executing {function_name}: {str(e)}")
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "content": json.dumps({"error": str(e)})
                    })
            
            # Create messages for the final API call
            messages = [system_message, user_message]
            
            # Add the assistant message (with tool calls)
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls
            })
            
            # Add the tool results
            messages.extend(tool_results)
            
            # Make the final API call
            try:
                final_response = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False
                    }
                )
                
                if final_response.status_code != 200:
                    return {
                        "message": {
                            "content": f"Ollama API error: {final_response.text}"
                        }
                    }
                
                final_result = final_response.json()
                
                # Extract the message content
                if "message" in final_result and "content" in final_result["message"]:
                    content = final_result["message"]["content"]
                    return {
                        "message": {
                            "content": content
                        }
                    }
                
                # Fallback for unexpected response structure
                return {
                    "message": {
                        "content": f"Received final response from Confluence: {str(final_result)}"
                    }
                }
                
            except Exception as e:
                logger.error(f"Error in final API call: {str(e)}")
                return {
                    "message": {
                        "content": f"Error processing Confluence tool results: {str(e)}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error processing tool calls: {str(e)}")
            return {
                "message": {
                    "content": f"Error processing Confluence commands: {str(e)}"
                }
            }
    
    # Confluence API methods
    def _list_spaces(self):
        """List all spaces in Confluence."""
        try:
            # Use different endpoints for Cloud vs Server
            if self.is_cloud:
                # Confluence Cloud uses the v2 API
                url = f"{self.confluence_url}/wiki/api/v2/spaces"
            else:
                # Confluence Server uses the REST API
                url = f"{self.confluence_url}/rest/api/space"
                
            logger.info(f"Listing spaces using URL: {url}")
            response = requests.get(url, headers=self.get_auth_headers())
            
            # Log response details for debugging
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
            logger.info(f"Response content preview: {response.text[:200]}...") # Log first 200 chars
            
            response.raise_for_status()
            
            # Parse the response based on the instance type
            result = response.json()
            
            # Format the response to be consistent regardless of instance type
            if self.is_cloud:
                # Cloud response has results directly
                return result
            else:
                # Server response has results in a 'results' field
                return {"results": result.get("results", [])}
        except Exception as e:
            logger.error(f"Error listing spaces: {str(e)}")
            return {"error": str(e)}
    
    def _get_space(self, space_key):
        """Get details about a specific space."""
        try:
            url = f"{self.confluence_url}/wiki/api/v2/spaces/{space_key}"
            response = requests.get(url, headers=self.get_auth_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting space {space_key}: {str(e)}")
            return {"error": str(e)}
    
    def _list_pages(self, space_key, limit=25):
        """List pages in a space."""
        try:
            url = f"{self.confluence_url}/wiki/api/v2/spaces/{space_key}/pages?limit={limit}"
            response = requests.get(url, headers=self.get_auth_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error listing pages in space {space_key}: {str(e)}")
            return {"error": str(e)}
    
    def _get_page(self, page_id):
        """Get a specific page with its content."""
        try:
            url = f"{self.confluence_url}/wiki/api/v2/pages/{page_id}?body-format=storage"
            response = requests.get(url, headers=self.get_auth_headers())
            response.raise_for_status()
            page_data = response.json()
            
            # Convert Confluence storage format to Markdown
            # In a real implementation, you would use a proper converter
            # This is a simplified placeholder
            if "body" in page_data and "storage" in page_data["body"]:
                page_data["body"]["markdown"] = self._convert_to_markdown(page_data["body"]["storage"]["value"])
            
            return page_data
        except Exception as e:
            logger.error(f"Error getting page {page_id}: {str(e)}")
            return {"error": str(e)}
    
    def _create_page(self, space_key, title, content, parent_id=None):
        """Create a new page in a space."""
        try:
            url = f"{self.confluence_url}/wiki/api/v2/pages"
            
            # Convert Markdown to Confluence storage format
            # In a real implementation, you would use a proper converter
            storage_value = self._convert_to_storage(content)
            
            data = {
                "spaceId": space_key,
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": storage_value
                }
            }
            
            if parent_id:
                data["parentId"] = parent_id
            
            response = requests.post(url, headers=self.get_auth_headers(), json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating page in space {space_key}: {str(e)}")
            return {"error": str(e)}
    
    def _update_page(self, page_id, title, content, version):
        """Update an existing page."""
        try:
            url = f"{self.confluence_url}/wiki/api/v2/pages/{page_id}"
            
            # Convert Markdown to Confluence storage format
            storage_value = self._convert_to_storage(content)
            
            data = {
                "id": page_id,
                "status": "current",
                "title": title,
                "body": {
                    "representation": "storage",
                    "value": storage_value
                },
                "version": {
                    "number": version + 1
                }
            }
            
            response = requests.put(url, headers=self.get_auth_headers(), json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error updating page {page_id}: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_search_results(self, search_results, original_query):
        """Analyze search results and generate an answer using the LLM.
        
        This method takes the search results from Confluence and uses the LLM to
        generate a direct answer to the user's query based on the content found.
        
        Args:
            search_results (dict): The search results from Confluence
            original_query (str): The original user query
            
        Returns:
            dict: The original search results with an added 'analysis' field containing
                  the LLM's answer to the query
        """
        try:
            # Check if we have any results to analyze
            if not search_results or search_results.get("total_results", 0) == 0:
                search_results["analysis"] = "No relevant information found in Confluence to answer your query."
                return search_results
            
            # Prepare content for the LLM to analyze
            context = ""
            for i, result in enumerate(search_results.get("results", [])):
                title = result.get("title", "Untitled")
                content = result.get("content", "")
                excerpt = result.get("excerpt", "")
                
                # Use the full content if available, otherwise use the excerpt
                text_to_use = content if content else excerpt
                
                # Add this result to the context
                context += f"\n\nDocument {i+1}: {title}\n{text_to_use}\n"
            
            # Truncate context if it's too long (to avoid token limits)
            max_context_length = 10000  # Adjust based on model capabilities
            if len(context) > max_context_length:
                context = context[:max_context_length] + "..."
            
            # Prepare the system message for the LLM
            system_message = {
                "role": "system",
                "content": (
                    "You are a helpful assistant that analyzes information from Confluence. "
                    "Based on the search results provided, answer the user's question as accurately as possible. "
                    "If the search results don't contain enough information to answer the question, "
                    "clearly state what information is missing. "
                    "If the search results contain conflicting information, point this out and explain the different perspectives. "
                    "Always cite which document(s) you're getting information from."
                )
            }
            
            # Prepare the user message with the query and context
            user_message = {
                "role": "user",
                "content": f"Question: {original_query}\n\nSearch results from Confluence:\n{context}"
            }
            
            # Call the LLM to analyze the results
            model = os.environ.get("CONFLUENCE_ANALYSIS_MODEL", "llama3")  # Default to llama3 if not specified
            
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": [system_message, user_message],
                "stream": False
            }
            
            # Make the request to the Ollama API
            ollama_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api")
            response = requests.post(f"{ollama_url}/chat", json=payload)
            response.raise_for_status()
            
            # Extract the analysis from the response
            result = response.json()
            analysis = result.get("message", {}).get("content", "")
            
            # Add the analysis to the search results
            search_results["analysis"] = analysis
            
            return search_results
        except Exception as e:
            logger.error(f"Error analyzing search results: {str(e)}")
            search_results["analysis_error"] = str(e)
            return search_results
    
    def _search_pages(self, cql, limit=10, analyze_results=True):
        """Search Confluence content using CQL.
        
        Args:
            cql (str): The CQL query to search with
            limit (int): Maximum number of results to return
            analyze_results (bool): Whether to analyze results with LLM
            
        Returns:
            dict: Search results with optional analysis
        """
        try:
            # Format the CQL query correctly based on common patterns
            # This helps convert natural language queries into proper CQL syntax
            formatted_cql = self._format_cql_query(cql)
            
            # URL encode the CQL query
            import urllib.parse
            encoded_cql = urllib.parse.quote(formatted_cql)
            
            logger.info(f"Original CQL: {cql}")
            logger.info(f"Formatted CQL: {formatted_cql}")
            logger.info(f"Searching with encoded CQL: {encoded_cql}")
            
            # For Confluence Server, the correct search endpoint is different
            if self.is_cloud:
                url = f"{self.confluence_url}/wiki/rest/api/content/search?cql={encoded_cql}&limit={limit}"
            else:
                # For Confluence Server, use the appropriate endpoint
                url = f"{self.confluence_url}/rest/api/content/search?cql={encoded_cql}&limit={limit}"
            
            logger.info(f"Making request to URL: {url}")
            response = requests.get(url, headers=self.get_auth_headers())
            
            # Log the response status and content
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
            logger.info(f"Response content preview: {response.text[:500]}...") # Log first 500 chars to avoid excessive logging
            
            # Check for authentication issues
            if response.status_code == 401:
                return {
                    "error": "Authentication failed. Please check your API token and email address."
                }
            elif response.status_code == 403:
                return {
                    "error": "Authorization failed. Your API token does not have permission to access this resource."
                }
            
            # Check if we got HTML instead of JSON (likely a login page)
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type or '<!DOCTYPE html>' in response.text[:100]:
                return {
                    "error": "Authentication failed. Received HTML login page instead of JSON data. Please check your authentication configuration."
                }
                
            # Check for CQL syntax errors (400 status code)
            if response.status_code == 400:
                try:
                    error_json = response.json()
                    error_message = error_json.get('message', 'Invalid CQL syntax')
                    
                    # Provide a more user-friendly error message
                    return {
                        "error": f"CQL syntax error: {error_message}. Try using a simpler search query.",
                        "search_query": formatted_cql,
                        "total_results": 0,
                        "results": []
                    }
                except json.JSONDecodeError:
                    pass
            
            response.raise_for_status()
            
            # Try to parse the JSON response with detailed error handling
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Response content that failed to parse: {response.text[:1000]}")
                return {
                    "error": f"Failed to parse JSON response: {str(e)}. This may indicate an authentication issue or an incorrect API endpoint."
                }
            
            # Format the results for better display
            if 'results' in result and result['results']:
                formatted_results = []
                for page in result['results']:
                    page_id = page.get('id')
                    page_title = page.get('title', 'Untitled')
                    page_type = page.get('type', 'unknown')
                    space = page.get('space', {}).get('name', 'Unknown Space')
                    
                    # Get the URL for the page
                    if self.is_cloud:
                        page_url = f"{self.confluence_url}/wiki/spaces/{page.get('space', {}).get('key', '')}/pages/{page_id}"
                    else:
                        # For server instances, use the _links data if available
                        if '_links' in page and 'webui' in page['_links']:
                            webui_link = page['_links']['webui']
                            # Check if it's a relative URL
                            if webui_link.startswith('/'):
                                page_url = f"{self.confluence_url}{webui_link}"
                            else:
                                page_url = webui_link
                        else:
                            # Fallback URL format
                            space_key = page.get('space', {}).get('key', '')
                            page_url = f"{self.confluence_url}/display/{space_key}/{page_title.replace(' ', '+')}"
                    
                    # Fetch the content of the page for better search context
                    page_content = ""
                    page_excerpt = ""
                    try:
                        # Only fetch content for pages, not attachments or other types
                        if page_type == 'page':
                            # Get the page content using the content API
                            content_url = f"{self.confluence_url}/rest/api/content/{page_id}?expand=body.storage"
                            content_response = requests.get(content_url, headers=self.get_auth_headers())
                            if content_response.status_code == 200:
                                content_data = content_response.json()
                                if 'body' in content_data and 'storage' in content_data['body']:
                                    # Extract the HTML content
                                    html_content = content_data['body']['storage'].get('value', '')
                                    
                                    # Convert HTML to plain text (basic conversion)
                                    import re
                                    from html import unescape
                                    
                                    # Remove HTML tags
                                    plain_text = re.sub(r'<[^>]+>', ' ', html_content)
                                    # Decode HTML entities
                                    plain_text = unescape(plain_text)
                                    # Normalize whitespace
                                    plain_text = re.sub(r'\s+', ' ', plain_text).strip()
                                    
                                    # Store the full content
                                    page_content = plain_text
                                    
                                    # Extract a relevant excerpt based on search terms
                                    # This helps show the most relevant part of the content
                                    search_terms = []
                                    
                                    # Extract search terms from the CQL query
                                    term_matches = re.findall(r'text\s*~\s*"([^"]+)"', formatted_cql)
                                    if term_matches:
                                        search_terms.extend(term_matches)
                                    
                                    if search_terms:
                                        # Find the most relevant section containing the search terms
                                        best_excerpt = ""
                                        max_term_count = 0
                                        
                                        # Split content into chunks of ~500 chars with overlap
                                        chunk_size = 500
                                        overlap = 100
                                        chunks = []
                                        
                                        for i in range(0, len(plain_text), chunk_size - overlap):
                                            chunk = plain_text[i:i + chunk_size]
                                            if chunk:  # Skip empty chunks
                                                chunks.append(chunk)
                                        
                                        # Find the chunk with the most search term occurrences
                                        for chunk in chunks:
                                            term_count = 0
                                            for term in search_terms:
                                                term_count += chunk.lower().count(term.lower())
                                            
                                            if term_count > max_term_count:
                                                max_term_count = term_count
                                                best_excerpt = chunk
                                        
                                        if best_excerpt:
                                            page_excerpt = best_excerpt + '...' if len(best_excerpt) >= 300 else best_excerpt
                                        else:
                                            # Fallback to first 300 chars if no relevant section found
                                            page_excerpt = plain_text[:300] + '...' if len(plain_text) > 300 else plain_text
                                    else:
                                        # No search terms found, use the beginning of the content
                                        page_excerpt = plain_text[:300] + '...' if len(plain_text) > 300 else plain_text
                    except Exception as e:
                        logger.error(f"Error fetching content for page {page_id}: {str(e)}")
                    
                    # Add to formatted results
                    formatted_results.append({
                        "id": page_id,
                        "title": page_title,
                        "type": page_type,
                        "space": space,
                        "url": page_url,
                        "excerpt": page_excerpt,
                        "content": page_content
                    })
                
                search_result = {
                    "search_query": cql,
                    "total_results": result.get('size', 0),
                    "results": formatted_results
                }
                
                # If we found results, analyze them if requested
                if search_result["total_results"] > 0:
                    if analyze_results:
                        return self._analyze_search_results(search_result, cql)
                    else:
                        return search_result
                    
                # If no results and we have a complex query with AND, try with OR instead
                if search_result["total_results"] == 0 and ' AND ' in formatted_cql:
                    logger.info("No results found with AND query, trying with OR instead")
                    # Replace AND with OR for broader results
                    broader_cql = formatted_cql.replace(' AND ', ' OR ')
                    try:
                        # Search with the broader query
                        # Pass analyze_results=False to avoid recursive analysis
                        broader_result = self._search_pages(broader_cql, limit, analyze_results=False)
                        if broader_result.get("total_results", 0) > 0:
                            broader_result["search_query"] = cql  # Keep original query for reference
                            broader_result["note"] = "No exact matches found. Showing related results instead."
                            if analyze_results:
                                return self._analyze_search_results(broader_result, cql)
                            else:
                                return broader_result
                    except Exception as e:
                        logger.error(f"Error with broader search: {str(e)}")
                
                # If still no results, try extracting keywords and searching for them
                if search_result["total_results"] == 0:
                    # Extract keywords (words longer than 3 characters)
                    import re
                    keywords = [word for word in re.findall(r'\b\w{4,}\b', cql.lower()) 
                               if word not in ['with', 'that', 'this', 'from', 'have', 'what', 'when', 'where', 'which', 'about']]
                    
                    if keywords:
                        logger.info(f"Trying keyword search with: {keywords}")
                        # Try searching with the most specific keyword
                        keywords.sort(key=len, reverse=True)  # Sort by length, longest first
                        for keyword in keywords[:2]:  # Try the top 2 keywords
                            try:
                                # Pass analyze_results=False to avoid recursive analysis
                                keyword_result = self._search_pages(f'text ~ "{keyword}"', limit, analyze_results=False)
                                if keyword_result.get("total_results", 0) > 0:
                                    keyword_result["search_query"] = cql  # Keep original query for reference
                                    keyword_result["note"] = f"No exact matches found. Showing results for '{keyword}' instead."
                                    if analyze_results:
                                        return self._analyze_search_results(keyword_result, cql)
                                    else:
                                        return keyword_result
                            except Exception as e:
                                logger.error(f"Error with keyword search: {str(e)}")
                
                return search_result
            else:
                return {
                    "search_query": cql,
                    "total_results": 0,
                    "results": []
                }
        except Exception as e:
            logger.error(f"Error searching with CQL '{cql}': {str(e)}")
            return {"error": str(e)}
    
    def _format_cql_query(self, cql):
        """Format a CQL query to ensure it uses the correct syntax.
        
        This method helps convert natural language or simplified CQL queries
        into properly formatted CQL for Confluence.
        """
        import json
        import re
        
        # Log the original query for debugging
        logger.info(f"Original CQL: {cql}")
        
        # If the query is empty or None, return a default query
        if not cql or cql.strip() == "":
            return 'type = page'
            
        # Check if this is a complex CQL query with parentheses and special syntax
        # If so, we should preserve it rather than reformatting
        if cql.startswith('(') and ')' in cql and any(op in cql for op in ['title:', 'key:', 'space_key:', 'type:', 'status:']):
            # This looks like a structured CQL query from the LLM - extract meaningful terms
            terms = re.findall(r'\b\w{3,}\b', cql)
            # Filter out common CQL keywords
            cql_keywords = ['title', 'content', 'space', 'key', 'type', 'page', 'blog', 'status', 
                          'open', 'inprogress', 'and', 'or', 'not', 'label', 'space_key']
            meaningful_terms = [t for t in terms if t.lower() not in cql_keywords]
            
            if meaningful_terms:
                logger.info(f"Extracted meaningful terms from complex CQL: {meaningful_terms}")
                return f'text ~ "{" ".join(meaningful_terms)}"'
            else:
                # If we couldn't extract meaningful terms, use a generic search
                return 'type = page'
        
        # First, check if this looks like a CQL status query (which is likely from an LLM not following instructions)
        if cql.startswith('status:') or 'type:Page' in cql:
            # This is likely an LLM generating CQL directly - extract any useful terms
            terms = re.findall(r'\b\w{4,}\b', cql)
            useful_terms = [t for t in terms if t.lower() not in ['status', 'open', 'type', 'page']]
            
            if useful_terms:
                # Use these terms instead of the raw CQL
                return f'text ~ "{" ".join(useful_terms)}"'
            else:
                # Fallback to a general search
                return 'type = page'
            
        # Extract key terms from the query for better searching
        # This approach is more general and doesn't rely on special cases
        def extract_key_terms(query_text):
            # Remove common stop words and punctuation
            stop_words = ['a', 'an', 'the', 'in', 'on', 'at', 'for', 'to', 'with', 'by', 'about',
                         'how', 'what', 'when', 'where', 'who', 'which', 'why', 'and', 'or', 'not',
                         'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                         'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should', 'shall',
                         'may', 'might', 'must', 'find', 'search', 'information', 'documentation',
                         'docs', 'document', 'page', 'pages', 'content', 'confluence', 'give', 'tell',
                         'please', 'need', 'want', 'looking', 'help']
            
            # Clean the query text
            clean_text = re.sub(r'[^\w\s]', ' ', query_text.lower())
            words = clean_text.split()
            
            # Filter out stop words and short words
            key_terms = [word for word in words if word not in stop_words and len(word) > 2]
            
            # Sort by length (longer words are often more specific)
            key_terms.sort(key=len, reverse=True)
            
            return key_terms
            
        # Check if this is a question (starts with how, what, where, when, why, can, etc.)
        question_starters = ['how', 'what', 'where', 'when', 'why', 'can', 'do', 'is', 'are', 'should', 'could']
        if any(cql.lower().strip().startswith(starter) for starter in question_starters):
            # This is a natural language question, extract key terms
            key_terms = extract_key_terms(cql)
            
            if len(key_terms) >= 2:
                # Use the top 2-3 most specific terms for better results
                if len(key_terms) >= 3:
                    # For questions with 3+ key terms, try to use them all with OR for broader results
                    return f'text ~ "{key_terms[0]}" OR text ~ "{key_terms[1]}" OR text ~ "{key_terms[2]}"'
                else:
                    # For questions with exactly 2 key terms
                    return f'text ~ "{key_terms[0]}" OR text ~ "{key_terms[1]}"'
            elif len(key_terms) == 1:
                # Only one key term found
                return f'text ~ "{key_terms[0]}"'
            else:
                # No key terms found, use a more general search
                # Remove question words and use what's left
                for starter in question_starters:
                    if cql.lower().startswith(starter):
                        remaining_text = cql[len(starter):].strip()
                        if remaining_text:
                            # Remove any leading articles or prepositions
                            words_to_remove = ['a', 'an', 'the', 'about', 'for', 'to', 'on']
                            for word in words_to_remove:
                                if remaining_text.lower().startswith(word + ' '):
                                    remaining_text = remaining_text[len(word):].strip()
                            
                            if remaining_text:
                                return f'text ~ "{remaining_text}"'
                
                # If all else fails, just search for the whole query
                return f'text ~ "{cql}"'
            
        # Check if the query looks like a JSON array
        if (cql.startswith('[') and cql.endswith(']')) or (cql.startswith('"[') and cql.endswith(']"')):
            try:
                # Try to parse as JSON
                if cql.startswith('"[') and cql.endswith(']"'):
                    # Remove the outer quotes if they exist
                    cql = cql[1:-1]
                    
                query_parts = json.loads(cql)
                
                # If it's a list of terms, use the second one (usually the search term)
                if isinstance(query_parts, list) and len(query_parts) > 1:
                    # If the first part contains a field specifier like "contains:content"
                    if isinstance(query_parts[0], str) and ':' in query_parts[0]:
                        field_parts = query_parts[0].split(':')
                        if len(field_parts) == 2:
                            field_type = field_parts[1].lower()
                            search_term = query_parts[1]
                            
                            # Map common field types to CQL syntax
                            if field_type in ['content', 'body']:
                                return f'text ~ "{search_term}"'
                            elif field_type in ['title']:
                                return f'title ~ "{search_term}"'
                            else:
                                return f'text ~ "{search_term}"'
                    
                    # Default to using the second term as the search term
                    return f'text ~ "{query_parts[1]}"'
                    
                # If it's a list with just one item, use that
                elif isinstance(query_parts, list) and len(query_parts) == 1:
                    return f'text ~ "{query_parts[0]}"'
                    
            except (json.JSONDecodeError, IndexError) as e:
                logger.warning(f"Failed to parse JSON-like query: {e}")
                
        # If the query already looks like proper CQL, return it as is
        if re.search(r'\b(text|title|content|space|label)\s*[~=]\s*"', cql):
            # Check if the CQL is properly formatted with quotes
            if cql.count('"') % 2 == 0:  # Even number of quotes
                logger.info(f"Query appears to be valid CQL, using as is: {cql}")
                return cql
            else:
                # Fix unbalanced quotes
                logger.warning(f"CQL has unbalanced quotes, attempting to fix: {cql}")
                # Extract the field and operator
                match = re.search(r'(\w+)\s*([~=])\s*"([^"]+)', cql)
                if match:
                    field, operator, term = match.groups()
                    return f'{field} {operator} "{term}"'
                
        # Check if this is a properly formatted CQL query with parentheses
        if '(' in cql and ')' in cql and any(op in cql for op in [' ~ "', ' = "']):
            # This looks like valid CQL syntax, return it as is
            logger.info(f"Complex CQL query detected, using as is: {cql}")
            return cql
                
        # Check for square brackets which indicate Confluence Server CQL syntax
        if '[' in cql and ']' in cql:
            # Look for patterns like [title] ~ "term" or [content] ~ "term"
            match = re.search(r'\[(\w+)\]\s*~\s*"([^"]+)"', cql)
            if match:
                field, term = match.groups()
                # Format it correctly for the API
                return f'{field} ~ "{term}"'
        
        # Handle 'contains' syntax which is common in natural language queries
        if 'contains' in cql.lower():
            # Try to extract the term after 'contains'
            match = re.search(r'contains\s+["\']?([^"\']*)["\']*', cql.lower())
            if match:
                term = match.group(1).strip()
                if term:
                    # Check if the term has special characters that need escaping in CQL
                    # CQL requires escaping of: ", ~, *, ?, AND, OR, NOT
                    special_chars = ['"', '~', '*', '?']
                    needs_escaping = any(char in term for char in special_chars) or \
                                    any(word in term.upper().split() for word in ['AND', 'OR', 'NOT'])
                    
                    if needs_escaping:
                        # For terms with special characters, we'll use exact matching
                        # by wrapping the term in quotes and escaping any quotes inside
                        escaped_term = term.replace('"', '\\"')
                        return f'text ~ "{escaped_term}"'
                    else:
                        return f'text ~ "{term}"'
        
        # Handle common patterns
        if cql.startswith('contains:'):
            # Convert contains:term to text ~ "term"
            term = cql.replace('contains:', '').strip()
            return f'text ~ "{term}"'
            
        elif ':' in cql and not (cql.startswith('(') and cql.endswith(')')): 
            # Handle field:value patterns like content:Python API
            field, value = cql.split(':', 1)
            field = field.strip().lower()
            value = value.strip()
            
            # Map common field names to proper CQL syntax
            if field in ['content', 'body']:
                return f'text ~ "{value}"'
            elif field in ['title']:
                return f'title ~ "{value}"'
            elif field in ['label', 'labels']:
                return f'label = "{value}"'
            elif field in ['space']:
                return f'space = "{value}"'
            else:
                # Default to text search for unknown fields
                return f'text ~ "{value}"'
            
        elif 'AND' in cql.upper() or 'OR' in cql.upper():
            # Handle complex queries with boolean operators
            # First check if it's already in CQL format
            if re.search(r'\b(text|title|content|space|label)\s*[~=]\s*"[^"]+"\s+(AND|OR)\s+', cql, re.IGNORECASE):
                return cql  # Already in proper CQL format
                
            # Try to parse natural language with AND/OR
            # First, check if we're dealing with a query like "SSL certificates AND Polarion"
            if ' AND ' in cql.upper():
                parts = cql.upper().split(' AND ')
                if len(parts) == 2:
                    term1 = parts[0].strip().strip('"\'')
                    term2 = parts[1].strip().strip('"\'')
                    return f'text ~ "{term1}" AND text ~ "{term2}"'
            
            if ' OR ' in cql.upper():
                parts = cql.upper().split(' OR ')
                if len(parts) == 2:
                    term1 = parts[0].strip().strip('"\'')
                    term2 = parts[1].strip().strip('"\'')
                    return f'text ~ "{term1}" OR text ~ "{term2}"'
            
            # More complex parsing for multiple operators
            terms = re.split(r'\s+(AND|OR)\s+', cql, flags=re.IGNORECASE)
            operators = re.findall(r'\s+(AND|OR)\s+', cql, re.IGNORECASE)
            
            if terms and len(terms) > 1:
                formatted_terms = []
                for term in terms:
                    # Clean the term
                    clean_term = term.strip().strip('"\'')
                    if clean_term:
                        # Check if the term has special characters that need escaping in CQL
                        special_chars = ['"', '~', '*', '?']
                        needs_escaping = any(char in clean_term for char in special_chars)
                        
                        if needs_escaping:
                            # For terms with special characters, escape them properly
                            escaped_term = clean_term.replace('"', '\\"')
                            formatted_terms.append(f'text ~ "{escaped_term}"')
                        else:
                            formatted_terms.append(f'text ~ "{clean_term}"')
                
                # Reconstruct the query with proper CQL syntax
                result = formatted_terms[0]
                for i in range(len(operators)):
                    result += f" {operators[i]} {formatted_terms[i+1]}"
                    
                # Log the formatted complex query
                logger.info(f"Formatted complex query: {result}")
                return result
            else:
                # Fallback to simple search if parsing fails
                clean_query = cql.replace('"', '')
                return f'text ~ "{clean_query}"'
        
        # Handle natural language queries by extracting key terms
        elif any(word in cql.lower() for word in ['about', 'find', 'search', 'information', 'documentation', 'how to', 'guide']):
            key_terms = extract_key_terms(cql)
            
            if key_terms:
                # Use the top 2 most specific terms for better results
                if len(key_terms) >= 2:
                    return f'text ~ "{key_terms[0]}" AND text ~ "{key_terms[1]}"'
                else:
                    return f'text ~ "{key_terms[0]}"'
            else:
                # If no key terms found, use the original query
                clean_query = re.sub(r'[^\w\s]', ' ', cql).strip()
                return f'text ~ "{clean_query}"'
            
        else:
            # Simple term, search in text (title and content)
            # Remove any quotes that might be present
            term = cql.strip('"\'')
            return f'text ~ "{term}"'
    
    def _get_labels(self, page_id):
        """Get labels for a page."""
        try:
            url = f"{self.confluence_url}/wiki/rest/api/content/{page_id}/label"
            response = requests.get(url, headers=self.get_auth_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting labels for page {page_id}: {str(e)}")
            return {"error": str(e)}
    
    def _add_label(self, page_id, label):
        """Add a label to a page."""
        try:
            url = f"{self.confluence_url}/wiki/rest/api/content/{page_id}/label"
            data = [{"name": label}]
            response = requests.post(url, headers=self.get_auth_headers(), json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error adding label '{label}' to page {page_id}: {str(e)}")
            return {"error": str(e)}
    
    def _remove_label(self, page_id, label):
        """Remove a label from a page."""
        try:
            url = f"{self.confluence_url}/wiki/rest/api/content/{page_id}/label/name/{label}"
            response = requests.delete(url, headers=self.get_auth_headers())
            response.raise_for_status()
            return {"success": True, "message": f"Label '{label}' removed from page {page_id}"}
        except Exception as e:
            logger.error(f"Error removing label '{label}' from page {page_id}: {str(e)}")
            return {"error": str(e)}
    
    # Helper methods for content conversion
    def _convert_to_markdown(self, storage_value):
        """
        Convert Confluence storage format to Markdown.
        
        This is a simplified placeholder. In a real implementation,
        you would use a proper converter library.
        """
        # This is a very simplified conversion
        # In reality, you would use a proper HTML-to-Markdown converter
        import re
        
        # Remove XML/HTML tags (very simplified)
        markdown = re.sub(r'<[^>]+>', '', storage_value)
        
        return markdown
    
    def _convert_to_storage(self, markdown):
        """
        Convert Markdown to Confluence storage format.
        
        This is a simplified placeholder. In a real implementation,
        you would use a proper converter library.
        """
        # This is a very simplified conversion
        # In reality, you would use a proper Markdown-to-HTML converter
        import re
        
        # Convert headers
        storage = re.sub(r'^# (.+)$', r'<h1>\1</h1>', markdown, flags=re.MULTILINE)
        storage = re.sub(r'^## (.+)$', r'<h2>\1</h2>', storage, flags=re.MULTILINE)
        
        # Convert paragraphs
        storage = re.sub(r'^([^<\n].+)$', r'<p>\1</p>', storage, flags=re.MULTILINE)
        
        return storage


def get_confluence_mcp_integration(confluence_url=None, api_token=None):
    """
    Get a singleton instance of the ConfluenceMCPIntegration.
    
    Args:
        confluence_url: The URL of your Confluence Cloud instance
        api_token: Your Confluence API token
        
    Returns:
        An instance of ConfluenceMCPIntegration
    """
    if not hasattr(get_confluence_mcp_integration, "instance"):
        get_confluence_mcp_integration.instance = ConfluenceMCPIntegration(
            confluence_url=confluence_url,
            api_token=api_token
        )
    return get_confluence_mcp_integration.instance

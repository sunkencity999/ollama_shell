#!/usr/bin/env python3
"""
Ollama Shell Jira MCP Integration

This module provides the interface between Ollama Shell and the Jira MCP integration,
allowing users to interact with Jira through natural language commands.
"""

import os
import sys
import json
import re
import logging
from typing import Dict, List, Any, Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ollama_shell_jira")

# Import the Jira MCP integration
try:
    from jira_mcp_integration import get_jira_mcp_integration
    JIRA_MCP_AVAILABLE = True
except ImportError:
    JIRA_MCP_AVAILABLE = False
    logger.warning("Jira MCP integration not available. Please install the required dependencies.")

# Rich console for pretty output
console = Console()

def get_ollama_shell_jira_mcp():
    """
    Get the Jira MCP integration instance.
    
    Returns:
        The Jira MCP integration instance or None if not available
    """
    if not JIRA_MCP_AVAILABLE:
        return None
    
    return get_jira_mcp_integration()

def handle_jira_nl_command(command: str, model: str = "llama3") -> Dict[str, Any]:
    """
    Handle a natural language command related to Jira.
    
    Args:
        command: The natural language command to execute
        model: The Ollama model to use for processing the command
        
    Returns:
        The result of the command execution as a dictionary with the following keys:
        - success: Boolean indicating if the command was successful
        - error: An error message if success is False
        - results: A list of issue dictionaries if applicable
        - query: The original query if applicable
        - formatted_query: The formatted JQL query if applicable
        - total: The total number of results if applicable
        - analysis: A string analysis of the results if applicable
    """
    try:
        if not JIRA_MCP_AVAILABLE:
            return {
                "success": False,
                "error": "Jira MCP integration not available. Please install the required dependencies.",
                "results": [],
                "query": command,
                "formatted_query": "",
                "total": 0,
                "analysis": ""
            }
        
        # Get the Jira MCP integration instance
        jira_mcp = get_jira_mcp_integration()
        
        # Define the generate_jql_from_nl function
        def generate_jql_from_nl(query: str, model: str = "llama3") -> str:
            """
            Generate a JQL query from natural language using pattern matching.
            
            Args:
                query: The natural language query
                model: The Ollama model to use for processing
                
            Returns:
                A JQL query string
            """
            try:
                # Simple pattern matching for common queries
                query_lower = query.lower().strip()
                
                # Check for 'my' pattern (assigned to me)
                if re.search(r'\bmy\b', query_lower):
                    if 'open' in query_lower or 'active' in query_lower or 'unresolved' in query_lower:
                        return 'assignee = currentUser() AND resolution = Unresolved'
                    elif 'closed' in query_lower or 'resolved' in query_lower:
                        return 'assignee = currentUser() AND resolution != Unresolved'
                    else:
                        return 'assignee = currentUser()'
                
                # Check for specific project
                project_match = re.search(r'project\s+["\']([^"\']*)["\'"\']', query_lower) or \
                               re.search(r'project\s+([^\s,\.]+)', query_lower)
                if project_match:
                    project_name = project_match.group(1).strip()
                    return f'project = "{project_name}"'
                
                # Check for specific status
                status_match = re.search(r'status\s+["\']([^"\']*)["\'"\']', query_lower) or \
                             re.search(r'status\s+([^\s,\.]+)', query_lower)
                if status_match:
                    status_name = status_match.group(1).strip()
                    return f'status = "{status_name}"'
                
                # Check for specific issue type
                type_match = re.search(r'type\s+["\']([^"\']*)["\'"\']', query_lower) or \
                           re.search(r'type\s+([^\s,\.]+)', query_lower)
                if type_match:
                    type_name = type_match.group(1).strip()
                    return f'issuetype = "{type_name}"'
                
                # Default to a text search if no specific patterns match
                search_terms = query_lower.split()
                search_terms = [term for term in search_terms if term not in ['search', 'find', 'list', 'query', 'provide', 'issues', 'jira']]
                search_query = ' '.join(search_terms)
                
                logger.info(f"Generated JQL query for general search: {search_query}")
                return search_query
            except Exception as e:
                logger.error(f"Error generating JQL from natural language: {e}")
                raise
        
        # Check if the integration is configured
        if not jira_mcp.is_configured():
            return {
                "success": False,
                "error": "Jira integration is not configured. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_KEY.",
                "results": [],
                "query": command,
                "formatted_query": "",
                "total": 0,
                "analysis": ""
            }
        
        # Process the command based on keywords
        command_lower = command.strip().lower()
        
        # Search for issues
        if any(keyword in command_lower for keyword in ["search", "find", "list", "query", "provide"]):
            # Check for specific patterns and convert to proper JQL
            
            # Check for assignee pattern
            if "assignee" in command_lower or "assigned to" in command_lower:
                # Extract the assignee name
                assignee_match = re.search(r'assignee\s+["\']([^"\']*)["\'"\']', command_lower) or \
                              re.search(r'assigned\s+to\s+["\']([^"\']*)["\'"\']', command_lower) or \
                              re.search(r'assignee\s+([^\s,\.]+)', command_lower) or \
                              re.search(r'assigned\s+to\s+([^\s,\.]+)', command_lower)
                
                if assignee_match:
                    assignee_name = assignee_match.group(1).strip()
                    # Create a proper JQL query for assignee
                    # Handle special cases for assignee
                    if assignee_name.lower() in ["me", "myself", "i", "my"]:
                        # Use currentUser() function for the current user
                        jql = 'assignee = currentUser()'
                        logger.info(f"Generated JQL query for current user: {jql}")
                    else:
                        # Try exact match with the full name
                        jql = f'assignee = "{assignee_name}"'
                        logger.info(f"Generated JQL query for assignee search: {jql}")
                    
                    try:
                        result = jira_mcp.jql_search(jql)
                        
                        # Ensure the result has the expected structure
                        if not isinstance(result, dict):
                            logger.error(f"Unexpected result type from jql_search: {type(result)}")
                            return {
                                "success": False,
                                "error": "Unexpected result type from Jira API",
                                "results": [],
                                "query": command,
                                "formatted_query": jql,
                                "total": 0,
                                "analysis": ""
                            }
                        
                        # If the search was successful and returned results, return them
                        if result.get("success", False) and result.get("results", []):
                            return result
                        
                        # If no results were found with the exact name, try a more flexible search
                        if assignee_name.lower() not in ["me", "myself", "i", "my"]:
                            # Try with contains operator for partial name match
                            jql = f'assignee ~ "{assignee_name}"'
                            logger.info(f"Trying alternative JQL query with contains operator: {jql}")
                            alt_result = jira_mcp.jql_search(jql)
                            
                            # Ensure the alternative result has the expected structure
                            if not isinstance(alt_result, dict):
                                logger.error(f"Unexpected result type from alternative jql_search: {type(alt_result)}")
                                return result  # Return the original result if the alternative search failed
                            
                            return alt_result
                        
                        # Return the original result if we couldn't find a better match
                        return result
                    except Exception as e:
                        logger.error(f"Error executing JQL search: {e}")
                        return {
                            "success": False,
                            "error": f"Error executing JQL search: {e}",
                            "results": [],
                            "query": command,
                            "formatted_query": jql,
                            "total": 0,
                            "analysis": ""
                        }
            
            # Check for other specific patterns here...
            # For example: status, priority, project, etc.
            
            # Default case: simple text search
            jql = command
            for keyword in ["search", "find", "list", "query", "provide", "issues", "for", "with", "jql", "please", "of", "a", "the"]:
                jql = re.sub(r'\b' + keyword + r'\b', "", jql, flags=re.IGNORECASE)
            jql = jql.strip()
            
            # Execute the search
            try:
                logger.info(f"Generated JQL query for general search: {jql}")
                return jira_mcp.jql_search(jql)
            except Exception as e:
                logger.error(f"Error executing general JQL search: {e}")
                return {
                    "success": False,
                    "error": f"Error executing JQL search: {e}",
                    "results": [],
                    "query": command,
                    "formatted_query": jql,
                    "total": 0,
                    "analysis": ""
                }
        
        # Get issue details
        elif any(keyword in command_lower for keyword in ["get", "show", "details", "info"]) and any(c.isalpha() and c.isupper() for c in command.split()):
            # Extract the issue key from the command
            words = command.split()
            issue_key = None
            for word in words:
                if any(c.isalpha() and c.isupper() for c in word) and "-" in word:
                    issue_key = word.upper()
                    break
            
            if issue_key:
                # Execute the get issue request
                try:
                    return jira_mcp.get_issue(issue_key)
                except Exception as e:
                    logger.error(f"Error getting issue details: {e}")
                    return {
                        "success": False,
                        "error": f"Error getting issue details: {e}",
                        "key": issue_key,
                        "summary": "",
                        "description": "",
                        "status": "",
                        "type": "",
                        "priority": "",
                        "assignee": "",
                        "reporter": "",
                        "created": "",
                        "updated": "",
                        "comments": [],
                        "url": ""
                    }
            else:
                return {
                    "success": False,
                    "error": "No valid issue key found in the command. Please specify an issue key (e.g., PROJECT-123).",
                    "key": "",
                    "summary": "",
                    "description": "",
                    "status": "",
                    "type": "",
                    "priority": "",
                    "assignee": "",
                    "reporter": "",
                    "created": "",
                    "updated": "",
                    "comments": [],
                    "url": ""
                }
        
        # Default case: use the LLM to generate a JQL query
        else:
            try:
                # Use the LLM to generate a JQL query
                jql = generate_jql_from_nl(command, model)
                
                # Execute the search
                logger.info(f"Generated JQL query from LLM: {jql}")
                result = jira_mcp.jql_search(jql)
                
                # Ensure result is a properly structured dictionary
                if not isinstance(result, dict):
                    logger.warning(f"Unexpected result type from jql_search: {type(result)}")
                    result = {
                        "success": False,
                        "error": "Unexpected response format from Jira search",
                        "results": [],
                        "query": jql,
                        "formatted_query": jql,
                        "total": 0,
                        "analysis": "Analysis unavailable due to unexpected response format."
                    }
                
                # Ensure all required keys exist in the result dictionary
                required_keys = ["success", "query", "formatted_query", "total", "results", "analysis"]
                for key in required_keys:
                    if key not in result:
                        logger.debug(f"Adding missing key to result: {key}")
                        if key == "analysis":
                            result[key] = "Analysis unavailable. Please check if Ollama service is running correctly."
                        elif key == "success":
                            result[key] = False
                        elif key == "total":
                            result[key] = len(result.get("results", []))
                        elif key == "results":
                            result[key] = []
                        else:
                            result[key] = ""
                
                # Handle None or error message in analysis - ensure this is done AFTER ensuring the key exists
                if "analysis" in result:
                    if result["analysis"] is None or result["analysis"] == "Error analyzing search results.":
                        logger.debug("Replacing None or error analysis with default message")
                        result["analysis"] = "Analysis unavailable. Please check if Ollama service is running correctly."
                else:
                    # This should never happen due to the previous loop, but adding as an extra safeguard
                    logger.warning("Analysis key still missing after ensuring required keys")
                    result["analysis"] = "Analysis unavailable. Please check if Ollama service is running correctly."
                
                # Log the result structure for debugging
                logger.debug(f"Result structure from jql_search: {list(result.keys())}")
                
                # Final safety check to ensure we never return None for analysis
                if "analysis" not in result or result["analysis"] is None:
                    logger.warning("Final safety check: Adding missing or None analysis")
                    result["analysis"] = "Analysis unavailable. Please check if Ollama service is running correctly."
                
                return result
            except Exception as e:
                logger.error(f"Error generating JQL from natural language: {e}")
                return {
                    "success": False,
                    "error": f"Error generating JQL from natural language: {str(e)}",
                    "results": [],
                    "query": command,
                    "formatted_query": "",
                    "total": 0,
                    "analysis": "Analysis unavailable due to an error processing your command."
                }
    except Exception as e:
        logger.error(f"Unexpected error in handle_jira_nl_command: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "results": [],
            "query": command,
            "formatted_query": "",
            "total": 0,
            "analysis": "Analysis unavailable due to an unexpected error."
        }

def display_jira_result(result: Dict[str, Any]) -> None:
    """
    Display the result of a Jira command in a rich format.
    
    Args:
        result: The result of the command execution
    """
    # Handle case where result is None or not a dictionary
    if result is None:
        console.print(Panel("[bold red]Error:[/bold red] No result returned from Jira command.", 
                          title="Jira Error", 
                          border_style="red"))
        return
    
    # Handle unsuccessful results
    if not result.get("success", False):
        # Display error message
        console.print(Panel(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}", 
                           title="Jira Error", 
                           border_style="red"))
        return
    
    # Check if this is a search result
    if "results" in result:
        # Display the search results
        display_jira_search_results(result)
        return
    
    # Check if this is a get issue result
    elif "key" in result and "summary" in result:
        # Display the issue details
        display_jira_issue_details(result)
        return
    
    # Check if this is an update or comment result
    elif "message" in result:
        # Display the success message
        console.print(Panel(f"[bold green]Success:[/bold green] {result.get('message', '')}", 
                           title="Jira Success", 
                           border_style="green"))
        return
    
    # Default case for unexpected result format
    console.print(Panel("[bold yellow]Success:[/bold yellow] Operation completed but no detailed information available.", 
                       title="Jira Success", 
                       border_style="yellow"))

def display_jira_search_results(result: Dict[str, Any]) -> None:
    """
    Display Jira search results in a rich format.
    
    Args:
        result: The search results
    """
    # Check if result is None or doesn't have the expected structure
    if result is None:
        console.print("[bold yellow]No search results available.[/bold yellow]")
        return
    
    # Extract the search results with safe defaults
    query = result.get("query", "")
    formatted_query = result.get("formatted_query", "")
    total = result.get("total", 0)
    results = result.get("results", [])
    analysis = result.get("analysis", "")
    
    # Display the search query and total results
    console.print(f"[bold]Search Query:[/bold] {query}")
    console.print(f"[bold]Formatted JQL:[/bold] {formatted_query}")
    console.print(f"[bold]Total Results:[/bold] {total}")
    
    # Display the analysis if available
    if analysis:
        console.print(Panel(Markdown(analysis), 
                           title="Analysis", 
                           border_style="blue"))
    
    # Display the search results in a table
    if results and isinstance(results, list) and len(results) > 0:
        table = Table(title=f"Jira Issues ({len(results)} of {total})")
        table.add_column("Key", style="cyan")
        table.add_column("Summary", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Type", style="magenta")
        table.add_column("Priority", style="red")
        table.add_column("Assignee", style="blue")
        
        for issue in results:
            if not isinstance(issue, dict):
                continue
                
            table.add_row(
                issue.get("key", ""),
                issue.get("summary", ""),
                issue.get("status", ""),
                issue.get("type", ""),
                issue.get("priority", ""),
                issue.get("assignee", "")
            )
        
        console.print(table)
        
        # Display the issue URLs without using Rich link markup
        console.print("\n[bold]Issue Links:[/bold]")
        for i, issue in enumerate(results):
            if not isinstance(issue, dict):
                continue
                
            issue_key = issue.get('key', '')
            issue_summary = issue.get('summary', '')
            issue_url = issue.get('url', '')
            
            # Format with a more obvious appearance but avoid using link markup
            if issue_url and issue_url.strip():
                console.print(f"[{i+1}] [bold blue]{issue_key} - {issue_summary}[/bold blue]")
                console.print(f"    URL: [blue]{issue_url}[/blue]")
            else:
                console.print(f"[{i+1}] [bold blue]{issue_key} - {issue_summary}[/bold blue]")
    else:
        console.print("[bold yellow]No issues found matching your query.[/bold yellow]")

def display_jira_issue_details(result: Dict[str, Any]) -> None:
    """
    Display Jira issue details in a rich format.
    
    Args:
        result: The issue details
    """
    # Check if result is None or doesn't have the expected structure
    if result is None:
        console.print("[bold yellow]No issue details available.[/bold yellow]")
        return
    
    # Check if the result has the minimum required fields
    if not result.get("key") or not result.get("summary"):
        console.print("[bold yellow]Incomplete issue details. The issue may not exist or you may not have permission to view it.[/bold yellow]")
        return
    
    # Extract the issue details with safe defaults
    key = result.get("key", "")
    summary = result.get("summary", "")
    description = result.get("description", "")
    status = result.get("status", "")
    issue_type = result.get("type", "")
    priority = result.get("priority", "")
    assignee = result.get("assignee", "")
    reporter = result.get("reporter", "")
    created = result.get("created", "")
    updated = result.get("updated", "")
    comments = result.get("comments", [])
    url = result.get("url", "")
    analysis = result.get("analysis", "")
    
    # Display the issue key and summary without using Rich link markup
    console.print(f"[bold]Issue:[/bold] [bold blue]{key}[/bold blue]")
    console.print(f"[bold]Summary:[/bold] {summary}")
    
    # Display URL if available
    if url and url.strip():
        console.print(f"[bold]URL:[/bold] [blue]{url}[/blue]")
    
    # Display the issue details in a table
    table = Table(title=f"Issue Details: {key}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Status", status)
    table.add_row("Type", issue_type)
    table.add_row("Priority", priority)
    table.add_row("Assignee", assignee)
    table.add_row("Reporter", reporter)
    table.add_row("Created", created)
    table.add_row("Updated", updated)
    
    console.print(table)
    
    # Display the issue description
    if description:
        try:
            console.print(Panel(Markdown(description), 
                              title="Description", 
                              border_style="blue"))
        except Exception as e:
            console.print(Panel(description, 
                              title="Description (Markdown rendering failed)", 
                              border_style="blue"))
    
    # Display the analysis if available
    if analysis:
        try:
            console.print(Panel(Markdown(analysis), 
                              title="Analysis", 
                              border_style="green"))
        except Exception as e:
            console.print(Panel(analysis, 
                              title="Analysis (Markdown rendering failed)", 
                              border_style="green"))
    
    # Display the comments
    if comments and isinstance(comments, list) and len(comments) > 0:
        console.print(f"\n[bold]Comments ({len(comments)}):[/bold]")
        for i, comment in enumerate(comments):
            if not isinstance(comment, dict):
                continue
                
            author = comment.get("author", "")
            body = comment.get("body", "")
            created = comment.get("created", "")
            
            try:
                console.print(Panel(Markdown(body), 
                                  title=f"Comment #{i+1} by {author} on {created}", 
                                  border_style="yellow"))
            except Exception as e:
                console.print(Panel(body, 
                                  title=f"Comment #{i+1} by {author} on {created} (Markdown rendering failed)", 
                                  border_style="yellow"))
    
    # Display the issue URL without using Rich link markup
    if url and url.strip():
        console.print(f"\n[bold]Issue URL:[/bold] [blue]{url}[/blue]")

def check_jira_configuration() -> tuple:
    """
    Check if the Jira MCP integration is properly configured.
    
    Returns:
        A tuple of (is_configured, message)
    """
    if not JIRA_MCP_AVAILABLE:
        return False, "Jira MCP integration not available. Please install the required dependencies."
    
    jira_mcp = get_jira_mcp_integration()
    
    if not jira_mcp.is_configured():
        return False, "Jira integration is not configured. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_KEY."
    
    return True, "Jira integration is configured and ready to use."

def save_jira_config(url: str, token: str, email: str) -> bool:
    """
    Save the Jira configuration to the .env file.
    
    Args:
        url: The Jira URL
        token: The Jira API token
        email: The Jira user email
        
    Returns:
        True if the configuration was saved successfully, False otherwise
    """
    # Create the Created Files directory if it doesn't exist
    created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Created Files')
    os.makedirs(created_files_dir, exist_ok=True)
    
    # Set up the config file path
    config_path = os.path.join(created_files_dir, 'jira_config.env')
    
    try:
        # Write the configuration to the file
        with open(config_path, 'w') as f:
            f.write(f"JIRA_URL={url}\n")
            f.write(f"JIRA_API_KEY={token}\n")
            f.write(f"JIRA_USER_EMAIL={email}\n")
        
        # Reload the environment variables
        os.environ["JIRA_URL"] = url
        os.environ["JIRA_API_KEY"] = token
        os.environ["JIRA_USER_EMAIL"] = email
        
        # Reinitialize the Jira MCP integration
        global _jira_mcp_integration
        _jira_mcp_integration = None
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving Jira configuration: {e}")
        return False

#!/usr/bin/env python3
"""
Jira Integration Example

This script demonstrates how to use the Jira MCP integration programmatically.
It shows how to search for issues, get issue details, add comments, and update issues.
"""

import os
import sys
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

# Add the parent directory to the path to import the Jira MCP integration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Jira MCP integration
try:
    from jira_mcp_integration import get_jira_mcp_integration
    from ollama_shell_jira_mcp import display_jira_result
except ImportError:
    print("Error: Jira MCP integration not found. Make sure you're running this script from the examples directory.")
    sys.exit(1)

# Rich console for pretty output
console = Console()

def main():
    """Main function to demonstrate the Jira MCP integration."""
    # Get the Jira MCP integration instance
    jira_mcp = get_jira_mcp_integration()
    
    # Check if the integration is configured
    if not jira_mcp.is_configured():
        console.print(Panel(
            "[bold red]Jira integration is not configured.[/bold red]\n\n"
            "Please set the following environment variables:\n"
            "- JIRA_URL\n"
            "- JIRA_USER_EMAIL\n"
            "- JIRA_API_KEY\n\n"
            "Or create a jira_config.env file in the Created Files directory.",
            title="Configuration Error",
            border_style="red"
        ))
        return
    
    # Display a welcome message
    console.print(Panel(
        "This example script demonstrates how to use the Jira MCP integration programmatically.\n"
        "It will show you how to search for issues, get issue details, add comments, and update issues.",
        title="Jira MCP Integration Example",
        border_style="blue"
    ))
    
    # Prompt for the action to perform
    console.print("\n[bold]Choose an action to perform:[/bold]")
    console.print("1. Search for issues")
    console.print("2. Get issue details")
    console.print("3. Add a comment to an issue")
    console.print("4. Update an issue")
    console.print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ")
    
    if choice == "1":
        # Search for issues
        console.print("\n[bold]Search for Issues[/bold]")
        jql = input("Enter a JQL query or natural language search: ")
        
        # Execute the search
        result = jira_mcp.jql_search(jql)
        
        # Display the result
        display_jira_result(result)
    
    elif choice == "2":
        # Get issue details
        console.print("\n[bold]Get Issue Details[/bold]")
        issue_key = input("Enter the issue key (e.g., PROJECT-123): ")
        
        # Execute the get issue request
        result = jira_mcp.get_issue(issue_key)
        
        # Display the result
        display_jira_result(result)
    
    elif choice == "3":
        # Add a comment to an issue
        console.print("\n[bold]Add a Comment to an Issue[/bold]")
        issue_key = input("Enter the issue key (e.g., PROJECT-123): ")
        comment = input("Enter your comment: ")
        
        # Execute the add comment request
        result = jira_mcp.add_comment(issue_key, comment)
        
        # Display the result
        display_jira_result(result)
    
    elif choice == "4":
        # Update an issue
        console.print("\n[bold]Update an Issue[/bold]")
        issue_key = input("Enter the issue key (e.g., PROJECT-123): ")
        
        # Prompt for the fields to update
        console.print("\n[bold]Choose a field to update:[/bold]")
        console.print("1. Status")
        console.print("2. Priority")
        console.print("3. Assignee")
        console.print("4. Summary")
        console.print("5. Description")
        
        field_choice = input("\nEnter your choice (1-5): ")
        
        fields = {}
        
        if field_choice == "1":
            # Update status
            status = input("Enter the new status: ")
            fields["status"] = {"name": status}
        
        elif field_choice == "2":
            # Update priority
            priority = input("Enter the new priority: ")
            fields["priority"] = {"name": priority}
        
        elif field_choice == "3":
            # Update assignee
            assignee = input("Enter the new assignee username: ")
            fields["assignee"] = {"name": assignee}
        
        elif field_choice == "4":
            # Update summary
            summary = input("Enter the new summary: ")
            fields["summary"] = summary
        
        elif field_choice == "5":
            # Update description
            description = input("Enter the new description: ")
            fields["description"] = description
        
        else:
            console.print("[bold red]Invalid choice.[/bold red]")
            return
        
        # Execute the update issue request
        result = jira_mcp.update_issue(issue_key, fields)
        
        # Display the result
        display_jira_result(result)
    
    elif choice == "5":
        # Exit
        console.print("\n[bold]Exiting...[/bold]")
        return
    
    else:
        console.print("[bold red]Invalid choice.[/bold red]")

if __name__ == "__main__":
    main()

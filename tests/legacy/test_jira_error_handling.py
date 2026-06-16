#!/usr/bin/env python3
"""
Test script for Jira integration error handling
"""

from jira_mcp_integration import JiraMCPIntegration
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("jira_test")

def test_error_handling():
    """Test the improved error handling in the Jira integration"""
    jira = JiraMCPIntegration()
    
    print("\n=== Testing get_issue with non-existent issue key ===")
    try:
        result = jira.get_issue('NONEXISTENT-123')
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing jql_search with invalid JQL ===")
    try:
        result = jira.jql_search('invalid jql syntax')
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing update_issue with non-existent issue key ===")
    try:
        result = jira.update_issue('NONEXISTENT-123', {'summary': 'Test update'})
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing add_comment with non-existent issue key ===")
    try:
        result = jira.add_comment('NONEXISTENT-123', 'Test comment')
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_error_handling()

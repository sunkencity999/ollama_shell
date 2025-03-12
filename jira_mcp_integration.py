#!/usr/bin/env python3
"""
Jira MCP Integration for Ollama Shell

This module integrates the Model Context Protocol (MCP) Jira server
with Ollama Shell, allowing LLMs to interact with Jira through
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
logger = logging.getLogger("jira_mcp")

# Load environment variables
# First try to load from the Created Files directory
created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Created Files')
config_path = os.path.join(created_files_dir, 'jira_config.env')

# Debug logging for configuration path
logger.info(f"Looking for Jira configuration at: {config_path}")
logger.info(f"Config file exists: {os.path.exists(config_path)}")

# Load from the Created Files directory if it exists, otherwise try the default .env file
if os.path.exists(config_path):
    logger.info("Loading Jira configuration from Created Files directory")
    try:
        # First try using dotenv
        load_dotenv(dotenv_path=config_path)
        
        # Then explicitly set environment variables from the file to ensure they're loaded
        with open(config_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    try:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
                        logger.info(f"Set environment variable: {key}")
                    except ValueError as e:
                        logger.error(f"Error parsing line in config file: {line.strip()}, Error: {e}")
    except Exception as e:
        logger.error(f"Error loading Jira configuration: {e}")
else:
    logger.info("Falling back to default .env file")
    load_dotenv()  # Fallback to default .env file

class JiraMCPIntegration:
    """
    Jira MCP Integration for Ollama Shell.
    
    This class provides methods to interact with Jira through
    the Model Context Protocol (MCP).
    """
    
    def __init__(self, jira_url=None, user_email=None, api_token=None):
        """
        Initialize the Jira MCP Integration.
        
        Args:
            jira_url: The URL of your Jira instance
            user_email: Your Jira user email
            api_token: Your Jira API token
        """
        # Log environment variables for debugging
        logger.info(f"Environment variables at initialization: JIRA_URL={os.getenv('JIRA_URL')}, JIRA_USER_EMAIL={os.getenv('JIRA_USER_EMAIL')}, JIRA_API_KEY={'*****' if os.getenv('JIRA_API_KEY') else None}")
        
        self.jira_url = jira_url or os.getenv("JIRA_URL")
        self.user_email = user_email or os.getenv("JIRA_USER_EMAIL")
        self.api_token = api_token or os.getenv("JIRA_API_KEY")
        
        # Log the actual values being used
        logger.info(f"Using Jira URL: {self.jira_url}")
        logger.info(f"Using Jira User Email: {self.user_email}")
        logger.info(f"Using Jira API Token: {'*****' if self.api_token else None}")
        
        # Check if the required environment variables are set
        if not self.jira_url:
            logger.warning("JIRA_URL is not set. Please set it in the environment variables.")
        if not self.user_email:
            logger.warning("JIRA_USER_EMAIL is not set. Please set it in the environment variables.")
        if not self.api_token:
            logger.warning("JIRA_API_KEY is not set. Please set it in the environment variables.")
        
        # Set up the Ollama API URL for LLM analysis
        self.ollama_api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api")
        self.analysis_model = os.getenv("JIRA_ANALYSIS_MODEL", "llama3")
        
        # Initialize the session with appropriate authentication
        self.session = requests.Session()
        if self.user_email and self.api_token:
            # Determine if this is a Jira Cloud or Server instance
            is_cloud = "atlassian.net" in self.jira_url if self.jira_url else False
            
            if is_cloud:
                # For Jira Cloud, use basic auth with email and token
                self.session.auth = (self.user_email, self.api_token)
                logger.info("Initialized Jira Cloud session with basic authentication")
            else:
                # For Jira Server, use the token in the Authorization header
                self.session.headers.update({
                    "Authorization": f"Bearer {self.api_token}"
                })
                logger.info("Initialized Jira Server session with Bearer token authentication")
                
            # Common headers for both Cloud and Server
            self.session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
    
    def _get_detailed_error_message(self, status_code, operation, issue_key=None):
        """
        Generate detailed error messages based on HTTP status codes.
        
        Args:
            status_code: The HTTP status code from the response
            operation: The operation being performed (e.g., 'updating issue', 'adding comment')
            issue_key: The Jira issue key if applicable
            
        Returns:
            A detailed error message with troubleshooting guidance
        """
        issue_context = f" {issue_key}" if issue_key else ""
        
        # Determine if this is a Jira Cloud or Server instance
        is_cloud = "atlassian.net" in self.jira_url if self.jira_url else False
        
        if status_code == 401:
            if is_cloud:
                return (
                    f"Authentication failed while {operation}{issue_context}. Your credentials are invalid or your API token has expired.\n\n"
                    f"Troubleshooting steps for Jira Cloud:\n"
                    f"1. Verify your JIRA_USER_EMAIL environment variable matches your Atlassian account email\n"
                    f"2. Check if your API token has expired\n"
                    f"3. Generate a new API token at https://id.atlassian.com/manage-profile/security/api-tokens\n"
                    f"4. Update your JIRA_API_KEY environment variable with the new token"
                )
            else:
                return (
                    f"Authentication failed while {operation}{issue_context}. Your credentials are invalid or your Personal Access Token has expired.\n\n"
                    f"Troubleshooting steps for Jira Server:\n"
                    f"1. Verify your JIRA_USER_EMAIL environment variable is set to your Jira Server username (not email)\n"
                    f"2. Check if your Personal Access Token (PAT) has expired\n"
                    f"3. Generate a new Personal Access Token in your Jira Server instance\n"
                    f"4. Update your JIRA_API_KEY environment variable with the new token\n"
                    f"5. Ensure the token is being used with Bearer authentication"
                )
        elif status_code == 403:
            return (
                f"Authorization failed while {operation}{issue_context}. You don't have sufficient permissions.\n\n"
                f"Troubleshooting steps:\n"
                f"1. Verify you have the required permissions in Jira for this operation\n"
                f"2. Contact your Jira administrator to request necessary permissions\n"
                f"3. Check if your Jira instance has restrictions on API access"
            )
        elif status_code == 404:
            if issue_key:
                return (
                    f"Resource not found while {operation}{issue_context}. The issue may not exist or you may not have permission to access it.\n\n"
                    f"Troubleshooting steps:\n"
                    f"1. Verify the issue key is correct\n"
                    f"2. Check if you can access this issue in the Jira web interface\n"
                    f"3. Ensure you have the necessary permissions to view this issue"
                )
            else:
                return (
                    f"Resource not found while {operation}. The requested Jira resource does not exist.\n\n"
                    f"Troubleshooting steps:\n"
                    f"1. Verify your JIRA_URL environment variable is correct\n"
                    f"2. Ensure the Jira instance is accessible"
                )
        elif status_code == 400:
            return (
                f"Bad request while {operation}{issue_context}. The data provided is invalid.\n\n"
                f"Troubleshooting steps:\n"
                f"1. Check the format and content of your request\n"
                f"2. Ensure all required fields are provided and have valid values\n"
                f"3. Verify field names match the Jira field schema"
            )
        else:
            return f"HTTP Error while {operation}{issue_context}: Status code {status_code}"
    
    def is_configured(self) -> bool:
        """
        Check if the Jira MCP Integration is configured.
        
        Returns:
            True if the integration is configured, False otherwise
        """
        # Log the configuration status for debugging
        logger.info(f"Checking Jira configuration status:")
        logger.info(f"  - JIRA_URL: {'Set' if self.jira_url else 'Not set'}")
        logger.info(f"  - JIRA_USER_EMAIL: {'Set' if self.user_email else 'Not set'}")
        logger.info(f"  - JIRA_API_KEY: {'Set' if self.api_token else 'Not set'}")
        
        configured = all([self.jira_url, self.user_email, self.api_token])
        logger.info(f"Jira integration is {'configured' if configured else 'not configured'}")
        return configured
    
    def _format_jql_query(self, jql: str) -> str:
        """
        Format a JQL query to ensure it uses the correct syntax.
        
        Args:
            jql: The JQL query to format
            
        Returns:
            The formatted JQL query
        """
        # If the query is already in JQL format, return it as is
        if "=" in jql or "~" in jql or ">" in jql or "<" in jql:
            return jql
        
        # Simple text search if no JQL operators are found
        return f'text ~ "{jql}"'
    
    def jql_search(self, jql: str, max_results: int = 10, fields: List[str] = None) -> Dict[str, Any]:
        """
        Search for issues in Jira using JQL.
        
        Args:
            jql: The JQL query to execute
            max_results: The maximum number of results to return
            fields: The fields to include in the response
            
        Returns:
            The search results as a dictionary with the following keys:
            - success: Boolean indicating if the search was successful
            - query: The original JQL query
            - formatted_query: The formatted JQL query
            - total: The total number of results
            - results: A list of issue dictionaries
            - analysis: A string analysis of the results
            - error: An error message if success is False
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Jira integration is not configured. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_KEY.",
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": "Analysis unavailable: Jira integration is not configured."
            }
        
        # Format the JQL query
        try:
            formatted_jql = self._format_jql_query(jql)
        except Exception as e:
            logger.error(f"Error formatting JQL query: {e}")
            return {
                "success": False,
                "error": f"Error formatting JQL query: {e}",
                "query": jql,
                "formatted_query": "",
                "total": 0,
                "results": [],
                "analysis": ""
            }
        
        # Set up the default fields if none are provided
        if fields is None:
            fields = ["summary", "description", "status", "assignee", "reporter", "created", "updated", "issuetype", "priority"]
        
        # Set up the API endpoint
        endpoint = f"{self.jira_url}/rest/api/2/search"
        
        # Set up the query parameters
        params = {
            "jql": formatted_jql,
            "maxResults": max_results,
            "fields": ",".join(fields)
        }
        
        try:
            # Execute the search
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Extract the issues
            issues = data.get("issues", [])
            
            # Format the results
            results = []
            for issue in issues:
                if not issue or not isinstance(issue, dict):
                    continue
                    
                issue_key = issue.get("key")
                if not issue_key:
                    continue
                    
                issue_fields = issue.get("fields", {})
                if not isinstance(issue_fields, dict):
                    issue_fields = {}
                
                # Extract the issue details with safe defaults
                summary = issue_fields.get("summary", "")
                description = issue_fields.get("description", "")
                
                # Safely extract nested properties
                status_obj = issue_fields.get("status", {})
                status = status_obj.get("name", "") if isinstance(status_obj, dict) else ""
                
                issuetype_obj = issue_fields.get("issuetype", {})
                issue_type = issuetype_obj.get("name", "") if isinstance(issuetype_obj, dict) else ""
                
                priority_obj = issue_fields.get("priority", {})
                priority = priority_obj.get("name", "") if isinstance(priority_obj, dict) else ""
                
                assignee_obj = issue_fields.get("assignee", {})
                assignee = assignee_obj.get("displayName", "Unassigned") if isinstance(assignee_obj, dict) else "Unassigned"
                
                reporter_obj = issue_fields.get("reporter", {})
                reporter = reporter_obj.get("displayName", "") if isinstance(reporter_obj, dict) else ""
                
                created = issue_fields.get("created", "")
                updated = issue_fields.get("updated", "")
                
                # Format the issue details
                issue_url = f"{self.jira_url}/browse/{issue_key}"
                
                results.append({
                    "key": issue_key,
                    "summary": summary,
                    "description": description,
                    "status": status,
                    "type": issue_type,
                    "priority": priority,
                    "assignee": assignee,
                    "reporter": reporter,
                    "created": created,
                    "updated": updated,
                    "url": issue_url
                })
            
            # Analyze the results if there are any
            analysis = ""
            if results:
                try:
                    analysis = self._analyze_search_results(results, jql)
                except Exception as e:
                    logger.error(f"Error analyzing search results: {e}")
                    analysis = "Error analyzing search results."
            
            return {
                "success": True,
                "query": jql,
                "formatted_query": formatted_jql,
                "total": data.get("total", 0),
                "results": results,
                "analysis": analysis
            }
        
        except requests.exceptions.HTTPError as e:
            status_code = 'unknown'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            
            # Get detailed error message with troubleshooting guidance
            error_message = self._get_detailed_error_message(status_code, "searching Jira")
            
            # Log the error with additional details for debugging
            logger.error(f"HTTP Error searching Jira: {e} (Status code: {status_code})")
            response_text = 'No response content'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                response_text = e.response.text
            logger.error(f"Response content: {response_text}")
            logger.error(f"JQL query: {jql}")
            
            return {
                "success": False,
                "error": error_message,
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": f"Analysis unavailable: {error_message}"
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error searching Jira: {e}")
            return {
                "success": False,
                "error": f"Connection Error searching Jira: Could not connect to {self.jira_url}. Please check your network connection and Jira URL.",
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": f"Analysis unavailable: Connection error when searching Jira."
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error searching Jira: {e}")
            return {
                "success": False,
                "error": f"Timeout Error searching Jira: The request to Jira timed out.",
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": "Analysis unavailable: Request to Jira timed out."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Jira: {e}")
            return {
                "success": False,
                "error": f"Error searching Jira: {e}. Please check your Jira configuration."
            }
    
    def get_issue(self, issue_key: str, fields: List[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific issue.
        
        Args:
            issue_key: The issue key (e.g., PROJECT-123)
            fields: The fields to include in the response
            
        Returns:
            The issue details
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Jira integration is not configured. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_KEY."
            }
        
        # Set up the default fields if none are provided
        if fields is None:
            fields = ["summary", "description", "status", "assignee", "reporter", "created", "updated", "issuetype", "priority", "comment"]
        
        # Set up the API endpoint
        endpoint = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        
        # Set up the query parameters
        params = {
            "fields": ",".join(fields)
        }
        
        try:
            # Execute the request
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Extract the issue details
            issue_fields = data.get("fields", {})
            
            # Extract the issue details
            summary = issue_fields.get("summary", "")
            description = issue_fields.get("description", "")
            status = issue_fields.get("status", {}).get("name", "")
            issue_type = issue_fields.get("issuetype", {}).get("name", "")
            priority = issue_fields.get("priority", {}).get("name", "")
            assignee = issue_fields.get("assignee", {}).get("displayName", "Unassigned")
            reporter = issue_fields.get("reporter", {}).get("displayName", "")
            created = issue_fields.get("created", "")
            updated = issue_fields.get("updated", "")
            
            # Extract comments if available
            comments = []
            if "comment" in issue_fields:
                for comment in issue_fields["comment"].get("comments", []):
                    comments.append({
                        "author": comment.get("author", {}).get("displayName", ""),
                        "body": comment.get("body", ""),
                        "created": comment.get("created", "")
                    })
            
            # Format the issue details
            issue_url = f"{self.jira_url}/browse/{issue_key}"
            
            # Analyze the issue details
            analysis = self._analyze_issue(data, issue_key)
            
            return {
                "success": True,
                "key": issue_key,
                "summary": summary,
                "description": description,
                "status": status,
                "type": issue_type,
                "priority": priority,
                "assignee": assignee,
                "reporter": reporter,
                "created": created,
                "updated": updated,
                "comments": comments,
                "url": issue_url,
                "analysis": analysis
            }
        
        except requests.exceptions.HTTPError as e:
            status_code = 'unknown'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            
            # Get detailed error message with troubleshooting guidance
            error_message = self._get_detailed_error_message(status_code, "getting issue", issue_key)
            
            # Log the error with additional details for debugging
            logger.error(f"HTTP Error getting issue {issue_key}: {e} (Status code: {status_code})")
            response_text = 'No response content'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                response_text = e.response.text
            logger.error(f"Response content: {response_text}")
            
            return {
                "success": False,
                "error": error_message,
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": f"Analysis unavailable: {error_message}"
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error getting issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Connection Error getting issue {issue_key}: Could not connect to {self.jira_url}. Please check your network connection and Jira URL."
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error getting issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Timeout Error getting issue {issue_key}: The request to Jira timed out."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Error getting issue {issue_key}: {e}"
            }
    
    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing Jira issue.
        
        Args:
            issue_key: The issue key (e.g., PROJECT-123)
            fields: The fields to update
            
        Returns:
            The result of the update operation
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Jira integration is not configured. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_KEY."
            }
        
        # Set up the API endpoint
        endpoint = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        
        # Set up the request payload
        payload = {
            "fields": fields
        }
        
        try:
            # Execute the request
            response = self.session.put(endpoint, json=payload)
            response.raise_for_status()
            
            return {
                "success": True,
                "message": f"Issue {issue_key} updated successfully"
            }
        
        except requests.exceptions.HTTPError as e:
            status_code = 'unknown'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            
            # Get detailed error message with troubleshooting guidance
            error_message = self._get_detailed_error_message(status_code, "updating issue", issue_key)
            
            # Log the error with additional details for debugging
            logger.error(f"HTTP Error updating issue {issue_key}: {e} (Status code: {status_code})")
            response_text = 'No response content'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                response_text = e.response.text
            logger.error(f"Response content: {response_text}")
            
            return {
                "success": False,
                "error": error_message,
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": f"Analysis unavailable: {error_message}"
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error updating issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Connection Error updating issue {issue_key}: Could not connect to {self.jira_url}. Please check your network connection and Jira URL."
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error updating issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Timeout Error updating issue {issue_key}: The request to Jira timed out."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Error updating issue {issue_key}: {e}. Please check your Jira configuration."
            }
    
    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """
        Add a comment to an existing Jira issue.
        
        Args:
            issue_key: The issue key (e.g., PROJECT-123)
            comment: The comment text
            
        Returns:
            The result of the comment operation
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Jira integration is not configured. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_KEY."
            }
        
        # Set up the API endpoint
        endpoint = f"{self.jira_url}/rest/api/2/issue/{issue_key}/comment"
        
        # Set up the request payload
        payload = {
            "body": comment
        }
        
        try:
            # Execute the request
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            
            return {
                "success": True,
                "message": f"Comment added to issue {issue_key} successfully"
            }
        
        except requests.exceptions.HTTPError as e:
            status_code = 'unknown'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            
            # Get detailed error message with troubleshooting guidance
            error_message = self._get_detailed_error_message(status_code, "adding comment to issue", issue_key)
            
            # Log the error with additional details for debugging
            logger.error(f"HTTP Error adding comment to issue {issue_key}: {e} (Status code: {status_code})")
            response_text = 'No response content'
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                response_text = e.response.text
            logger.error(f"Response content: {response_text}")
            
            return {
                "success": False,
                "error": error_message,
                "query": jql,
                "formatted_query": jql,
                "total": 0,
                "results": [],
                "analysis": f"Analysis unavailable: {error_message}"
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error adding comment to issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Connection Error adding comment to issue {issue_key}: Could not connect to {self.jira_url}. Please check your network connection and Jira URL."
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error adding comment to issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Timeout Error adding comment to issue {issue_key}: The request to Jira timed out."
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding comment to issue {issue_key}: {e}")
            return {
                "success": False,
                "error": f"Error adding comment to issue {issue_key}: {e}. Please check your Jira configuration."
            }
    
    def _analyze_search_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """
        Analyze search results using the Ollama LLM.
        
        Args:
            results: The search results to analyze
            query: The original query
            
        Returns:
            The analysis of the search results
        """
        if not results:
            return "No issues found matching your query."
        
        # Skip LLM analysis if there are too few results
        if len(results) <= 2:
            return f"Found {len(results)} issues matching your query."
        
        # Prepare the prompt for the LLM
        prompt = f"""
        Analyze the following Jira issues based on the query: "{query}"
        
        Issues:
        """
        
        # Add the issues to the prompt
        for i, issue in enumerate(results[:5]):  # Limit to first 5 issues to avoid token limits
            prompt += f"""
            Issue {i+1}: {issue['key']} - {issue['summary']}
            Status: {issue['status']}
            Type: {issue['type']}
            Priority: {issue['priority']}
            Assignee: {issue['assignee']}
            Description: {issue['description'][:200]}...
            """
        
        prompt += """
        Please provide a concise summary of these issues, including:
        1. Common themes or patterns
        2. Status distribution
        3. Priority distribution
        4. Any actionable insights
        
        Keep your response under 200 words.
        """
        
        # Call the Ollama API
        try:
            # Log the API call for debugging
            logger.info(f"Calling Ollama API at: {self.ollama_api_url}/chat with model: {self.analysis_model}")
            
            # First check if Ollama service is available
            try:
                # Use a simple HEAD request to check if the service is running
                logger.debug(f"Checking if Ollama service is available at: {self.ollama_api_url.split('/api')[0]}")
                check_response = requests.head(f"{self.ollama_api_url.split('/api')[0]}", timeout=1)
                if check_response.status_code >= 400:
                    logger.warning(f"Ollama service returned status code {check_response.status_code}")
                    return f"Found {len(results)} issues matching your query. (Analysis unavailable: Ollama service returned status code {check_response.status_code})"
            except requests.exceptions.RequestException as e:
                logger.warning(f"Ollama service is not available: {e}")
                return f"Found {len(results)} issues matching your query. (Analysis unavailable: Ollama service is not running or not accessible)"
            
            # If we get here, the service appears to be running, so try the actual API call
            # Use the /chat endpoint instead of /generate to match the regular chat functionality
            logger.debug("Preparing to call Ollama API with chat endpoint")
            
            # First, check if the model exists
            try:
                models_response = requests.get(f"{self.ollama_api_url.split('/api')[0]}/api/tags", timeout=5)
                models_response.raise_for_status()
                models_json = models_response.json()
                logger.debug(f"Available models: {models_json}")
                
                # Check if our model is in the list
                model_exists = False
                if isinstance(models_json, dict) and "models" in models_json:
                    model_names = [model.get("name") for model in models_json.get("models", []) if isinstance(model, dict)]
                    logger.debug(f"Available model names: {model_names}")
                    if self.analysis_model in model_names:
                        model_exists = True
                        logger.debug(f"Model {self.analysis_model} exists")
                    else:
                        logger.warning(f"Model {self.analysis_model} not found in available models")
                else:
                    logger.warning(f"Unexpected models response format: {models_json}")
            except Exception as e:
                logger.warning(f"Error checking available models: {e}")
                # Continue anyway, as the model might still work
            
            # Log the request payload for debugging
            request_payload = {
                "model": self.analysis_model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that analyzes Jira issues and provides concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            }
            logger.debug(f"Request payload: {request_payload}")
            
            try:
                response = requests.post(
                    f"{self.ollama_api_url}/chat",
                    json=request_payload,
                    timeout=10  # Add a reasonable timeout
                )
                
                logger.debug(f"Response status code: {response.status_code}")
                response.raise_for_status()
                
                # Parse the response JSON
                logger.debug("Parsing response JSON")
                try:
                    response_json = response.json()
                    logger.debug(f"Response JSON parsed successfully: {type(response_json)}")
                except Exception as e:
                    logger.error(f"Error parsing response JSON: {e}")
                    logger.debug(f"Raw response content: {response.text}")
                    return f"Found {len(results)} issues matching your query. (Analysis unavailable: Error parsing response from Ollama API)"
            except Exception as e:
                logger.error(f"Error calling Ollama API: {e}")
                return f"Found {len(results)} issues matching your query. (Analysis unavailable: Error calling Ollama API: {str(e)})"
            
            # Log the response structure for debugging
            logger.debug(f"Ollama API response keys: {list(response_json.keys())}")
            
            # Extract the analysis from the response with better error handling
            # The chat endpoint returns a different structure than the generate endpoint
            analysis = ""
            try:
                # Log the full response for debugging
                logger.debug(f"Full Ollama API response: {response_json}")
                
                # Guard against None response
                if response_json is None:
                    logger.warning("Received None response from Ollama API")
                    return f"Found {len(results)} issues matching your query. (Analysis unavailable: Received empty response from Ollama API)"
                
                # Handle non-dict responses
                if not isinstance(response_json, dict):
                    logger.warning(f"Unexpected response type: {type(response_json)}")
                    # Try to convert to string if possible
                    try:
                        analysis = str(response_json)
                    except Exception as e:
                        logger.error(f"Error converting response to string: {e}")
                        analysis = "Analysis unavailable due to unexpected response format."
                    return analysis
                
                # Log all keys in the response
                response_keys = list(response_json.keys())
                logger.debug(f"Response keys: {response_keys}")
                
                # The /chat endpoint typically returns a structure with a "message" field
                if "message" in response_json:
                    logger.debug("Found 'message' key in response")
                    message = response_json.get("message")
                    
                    # Guard against None message
                    if message is None:
                        logger.warning("Message field is None in response")
                        return f"Found {len(results)} issues matching your query. (Analysis unavailable: Message field is empty)"
                    
                    logger.debug(f"Message value type: {type(message)}")
                    
                    # Handle dict message with content
                    if isinstance(message, dict):
                        message_keys = list(message.keys())
                        logger.debug(f"Message keys: {message_keys}")
                        
                        if "content" in message:
                            logger.debug("Found 'content' key in message")
                            content = message.get("content")
                            
                            # Guard against None content
                            if content is None:
                                logger.warning("Content field is None in message")
                                return f"Found {len(results)} issues matching your query. (Analysis unavailable: Content field is empty)"
                            
                            logger.debug(f"Content value type: {type(content)}")
                            analysis = str(content)
                        else:
                            logger.warning(f"No 'content' key in message. Available keys: {message_keys}")
                            # Try to use the first available key as fallback
                            if message_keys:
                                first_key = message_keys[0]
                                first_value = message.get(first_key)
                                if first_value is not None:
                                    analysis = str(first_value)
                                    logger.debug(f"Using '{first_key}' as fallback: {analysis[:50]}...")
                    # Handle string or other message types
                    elif message is not None:
                        logger.debug(f"Message is not a dict, using direct value: {type(message)}")
                        analysis = str(message)
                    else:
                        logger.warning("Message has unexpected format")
                
                # Check for other possible response formats as fallbacks
                elif "response" in response_json:
                    logger.debug("Found 'response' key in response")
                    response_value = response_json.get("response")
                    if response_value is not None:
                        analysis = str(response_value)
                    else:
                        logger.warning("Response field is None")
                
                elif "output" in response_json:
                    logger.debug("Found 'output' key in response")
                    output_value = response_json.get("output")
                    if output_value is not None:
                        analysis = str(output_value)
                    else:
                        logger.warning("Output field is None")
                
                elif "completion" in response_json:
                    logger.debug("Found 'completion' key in response")
                    completion_value = response_json.get("completion")
                    if completion_value is not None:
                        analysis = str(completion_value)
                    else:
                        logger.warning("Completion field is None")
                
                # Last resort: try to use any available key
                elif response_keys:
                    logger.warning(f"Could not find expected keys. Available keys: {response_keys}")
                    # Try the first key as fallback
                    first_key = response_keys[0]
                    first_value = response_json.get(first_key)
                    if first_value is not None:
                        try:
                            analysis = str(first_value)
                            logger.debug(f"Using '{first_key}' as fallback: {analysis[:50]}...")
                        except Exception as e:
                            logger.error(f"Error converting '{first_key}' to string: {e}")
                
                else:
                    logger.warning("Response has no keys")
            except Exception as e:
                logger.error(f"Error extracting analysis from response: {e}")
                # Log the response structure for debugging
                logger.debug(f"Response JSON: {response_json if 'response_json' in locals() else 'Not available'}")
                # Log the traceback for more detailed debugging
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return f"Found {len(results)} issues matching your query. (Analysis unavailable: Error processing response: {str(e)})"
            
            # If we still don't have an analysis, provide a default message
            if not analysis:
                analysis = f"Found {len(results)} issues matching your query. (Analysis unavailable. Please check if Ollama service is running correctly.)"
            
            logger.debug(f"Final analysis: {analysis[:100]}...")
            return analysis
        
        except requests.exceptions.HTTPError as e:
            status_code = 'unknown'
            if hasattr(e, 'response') and e.response is not None:
                if hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                # Log the response content for debugging
                if hasattr(e.response, 'text'):
                    logger.debug(f"Error response content: {e.response.text}")
            logger.error(f"HTTP Error analyzing search results: {e} (Status code: {status_code})")
            return f"Found {len(results)} issues matching your query. (Analysis unavailable: HTTP Error {status_code} from Ollama API)"
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error analyzing search results: {e}")
            return f"Found {len(results)} issues matching your query. (Analysis unavailable: Ollama service is not running or not accessible)"
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error analyzing search results: {e}")
            return f"Found {len(results)} issues matching your query. (Analysis unavailable: Request to Ollama API timed out)"
        
        except ValueError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return f"Found {len(results)} issues matching your query. (Analysis unavailable: Invalid response format from Ollama API)"
        
        except Exception as e:
            logger.error(f"Unexpected error analyzing search results: {e}")
            # Log the traceback for more detailed debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Found {len(results)} issues matching your query. (Analysis unavailable: {str(e)})"
            
    def _get_detailed_error_message(self, status_code, error_context=""):
        """Generate a detailed error message based on HTTP status code.
        
        Args:
            status_code: The HTTP status code
            error_context: Additional context about the error
            
        Returns:
            A detailed error message with troubleshooting steps
        """
        if status_code == 401:
            return (f"Authentication failed (401). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Verify your Jira API token is correct and not expired\n"
                   f"2. Check that your email address matches your Jira account\n"
                   f"3. Ensure your Jira URL is correct")
        elif status_code == 403:
            return (f"Authorization failed (403). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Verify you have the necessary permissions in Jira\n"
                   f"2. Check if your account has been restricted\n"
                   f"3. Contact your Jira administrator for assistance")
        elif status_code == 404:
            return (f"Resource not found (404). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Verify the issue key or resource identifier is correct\n"
                   f"2. Check if the resource has been deleted or moved\n"
                   f"3. Ensure your Jira URL is pointing to the correct instance")
        elif status_code == 400:
            return (f"Bad request (400). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Check the format of your request data\n"
                   f"2. Verify that all required fields are provided\n"
                   f"3. Ensure values are within acceptable ranges")
        elif status_code == 429:
            return (f"Rate limit exceeded (429). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Reduce the frequency of your requests\n"
                   f"2. Implement exponential backoff for retries\n"
                   f"3. Contact your Jira administrator about rate limits")
        elif status_code >= 500:
            return (f"Jira server error ({status_code}). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Wait and try again later\n"
                   f"2. Check Jira status page for outages\n"
                   f"3. Contact your Jira administrator")
        else:
            return (f"HTTP error ({status_code}). {error_context}\n\n"
                   f"Troubleshooting steps:\n"
                   f"1. Check your network connection\n"
                   f"2. Verify your Jira configuration\n"
                   f"3. Try again later or contact support")
    
    def _analyze_issue(self, issue_data: Dict[str, Any], issue_key: str) -> str:
        """
        Analyze an issue using the Ollama LLM.
        
        Args:
            issue_data: The issue data to analyze
            issue_key: The issue key
            
        Returns:
            The analysis of the issue
        """
        # Extract the issue fields
        fields = issue_data.get("fields", {})
        
        # Extract the issue details
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        status = fields.get("status", {}).get("name", "")
        issue_type = fields.get("issuetype", {}).get("name", "")
        priority = fields.get("priority", {}).get("name", "")
        assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
        
        # Extract comments if available
        comments = []
        if "comment" in fields:
            for comment in fields["comment"].get("comments", [])[:3]:  # Limit to first 3 comments
                comments.append({
                    "author": comment.get("author", {}).get("displayName", ""),
                    "body": comment.get("body", "")
                })
        
        # Prepare the prompt for the LLM
        prompt = f"""
        Analyze the following Jira issue:
        
        Key: {issue_key}
        Summary: {summary}
        Description: {description}
        Status: {status}
        Type: {issue_type}
        Priority: {priority}
        Assignee: {assignee}
        """
        
        # Add comments to the prompt if available
        if comments:
            prompt += "\nComments:\n"
            for i, comment in enumerate(comments):
                prompt += f"{i+1}. {comment['author']}: {comment['body'][:200]}...\n"
        
        prompt += """
        Please provide a concise analysis of this issue, including:
        1. Key points from the description
        2. Current status and next steps
        3. Any risks or blockers mentioned
        4. Recommendations for resolution
        
        Keep your response under 200 words.
        """
        
        # Call the Ollama API
        try:
            # First check if Ollama service is available
            try:
                service_check = requests.get(f"{self.ollama_api_url}/version", timeout=2)
                service_check.raise_for_status()
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                logger.error(f"Ollama service is not available: {e}")
                return "Analysis unavailable: Ollama service is not accessible. Please ensure it's running."
            
            # Use the /chat endpoint instead of /generate
            response = requests.post(
                f"{self.ollama_api_url}/chat",
                json={
                    "model": self.analysis_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that analyzes Jira issues and provides concise summaries."},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.7
                    }
                },
                timeout=10  # Add a reasonable timeout
            )
            response.raise_for_status()
            
            # Parse the response JSON
            response_json = response.json()
            
            # Extract the analysis from the response with better error handling
            analysis = ""
            try:
                # Log the full response for debugging
                logger.debug(f"Full Ollama API response for issue analysis: {response_json}")
                
                if response_json is None:
                    logger.warning("Received None response from Ollama API during issue analysis")
                elif not isinstance(response_json, dict):
                    logger.warning(f"Unexpected response type during issue analysis: {type(response_json)}")
                    analysis = str(response_json)
                else:
                    # The /chat endpoint typically returns a structure with a "message" field
                    if "message" in response_json:
                        message = response_json.get("message")
                        if message is None:
                            logger.warning("Message field is None in issue analysis response")
                        elif isinstance(message, dict) and "content" in message:
                            analysis = message.get("content", "")
                            if analysis is None:
                                analysis = ""
                                logger.warning("Content field is None in issue analysis message")
                        else:
                            logger.warning(f"Unexpected message format during issue analysis: {message}")
                    # Check for other possible response formats
                    elif "response" in response_json:
                        analysis = response_json.get("response", "")
                        if analysis is None:
                            analysis = ""
                            logger.warning("Response field is None in issue analysis")
                    elif "output" in response_json:
                        analysis = response_json.get("output", "")
                        if analysis is None:
                            analysis = ""
                            logger.warning("Output field is None in issue analysis")
                    elif "completion" in response_json:
                        analysis = response_json.get("completion", "")
                        if analysis is None:
                            analysis = ""
                            logger.warning("Completion field is None in issue analysis")
                    else:
                        logger.warning(f"Could not find content in issue analysis response. Keys: {list(response_json.keys())}")
            except Exception as e:
                logger.error(f"Error extracting issue analysis from response: {e}")
            
            # If we still don't have an analysis, provide a default message
            if not analysis:
                analysis = "Analysis unavailable. Please check if Ollama service is running correctly."
            
            return analysis
        
        except requests.exceptions.HTTPError as e:
            status_code = 'unknown'
            if hasattr(e, 'response') and e.response is not None:
                if hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
            logger.error(f"HTTP Error analyzing issue: {e} (Status code: {status_code})")
            return f"Analysis unavailable: HTTP Error {status_code} from Ollama API"
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error analyzing issue: {e}")
            return "Analysis unavailable: Ollama service is not running or not accessible"
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error analyzing issue: {e}")
            return "Analysis unavailable: Request to Ollama API timed out"
        
        except ValueError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return "Analysis unavailable: Invalid response format from Ollama API"
        
        except Exception as e:
            logger.error(f"Unexpected error analyzing issue: {e}")
            return f"Analysis unavailable: {str(e)}"

# Singleton instance
_jira_mcp_integration = None

def get_jira_mcp_integration(jira_url=None, user_email=None, api_token=None):
    """
    Get a singleton instance of the JiraMCPIntegration.
    
    Args:
        jira_url: The URL of your Jira instance
        user_email: Your Jira user email
        api_token: Your Jira API token
        
    Returns:
        An instance of JiraMCPIntegration
    """
    global _jira_mcp_integration
    
    if _jira_mcp_integration is None:
        _jira_mcp_integration = JiraMCPIntegration(jira_url, user_email, api_token)
    
    return _jira_mcp_integration

#!/usr/bin/env python3
"""
Updated Agentic Assistant Implementation

This file contains an updated implementation of the Agentic Assistant with improved
file creation task handling.
"""
import os
import re
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import the fixed file handler functions
from fixed_file_handler import extract_filename, display_file_result

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize console for rich output
console = Console()

class AgenticAssistant:
    """
    Agentic Assistant for handling various tasks.
    
    This class provides methods for executing different types of tasks using
    the Ollama API, including file creation, web browsing, and general tasks.
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the Agentic Assistant.
        
        Args:
            model: The Ollama model to use (optional)
        """
        from agentic_ollama import AgenticOllama
        
        # Initialize the Agentic Ollama instance
        self.agentic_ollama = AgenticOllama(model)
    
    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task based on its description.
        
        Args:
            task_description: Natural language description of the task to execute
            
        Returns:
            Dict containing the execution results
        """
        # Convert task description to lowercase for easier matching
        task_lower = task_description.lower()
        
        # Check for file creation tasks
        if (
            # File creation patterns
            ("create" in task_lower and ("file" in task_lower or "document" in task_lower or "story" in task_lower or "poem" in task_lower)) or \
            ("write" in task_lower and ("file" in task_lower or "document" in task_lower or "story" in task_lower or "poem" in task_lower)) or \
            # File saving patterns
            ("save" in task_lower and ("file" in task_lower or "document" in task_lower or "story" in task_lower or "poem" in task_lower)) or \
            # Complex patterns
            (("write" in task_lower or "create" in task_lower) and "save" in task_lower) or \
            # Fallback patterns
            (extract_filename(task_description) is not None)
        ):
            return await self._handle_file_creation(task_description)
        
        # Check for image analysis tasks
        elif (
            # Image analysis patterns
            ("analyze" in task_lower or "describe" in task_lower or "what's in" in task_lower or "what is in" in task_lower) and \
            ("image" in task_lower or "picture" in task_lower or "photo" in task_lower)
        ):
            return await self._handle_image_analysis(task_description)
        
        # Check for web browsing tasks
        elif (
            # Web browsing patterns
            ("browse" in task_lower or "go to" in task_lower or "visit" in task_lower or "open" in task_lower) and \
            ("website" in task_lower or "webpage" in task_lower or "site" in task_lower or "url" in task_lower or "http" in task_lower) or \
            # Information gathering patterns
            (("gather" in task_lower or "collect" in task_lower or "get" in task_lower) and \
             ("information" in task_lower or "data" in task_lower or "websites" in task_lower or "about" in task_lower)) or \
            # Web search patterns
            (("search" in task_lower or "find" in task_lower or "look up" in task_lower or "research" in task_lower) and \
             ("web" in task_lower or "internet" in task_lower or "online" in task_lower or "information" in task_lower)) or \
            # File saving patterns (indicating web content gathering)
            ("save" in task_lower and (".txt" in task_lower or "file" in task_lower or "document" in task_lower))
        ):
            return await self._handle_web_browsing_task(task_description)
        
        # General task execution
        else:
            return await self._handle_general_task(task_description)
    
    async def _handle_file_creation(self, task_description: str) -> Dict[str, Any]:
        """
        Handle file creation tasks.
        
        Args:
            task_description: Natural language description of the file to create
            
        Returns:
            Dict containing the file creation results
        """
        try:
            # Extract filename from task description if specified
            filename = extract_filename(task_description)
            
            # If a filename was found, modify the task to ensure it's used
            if filename:
                # Check if the task already has a "save as" or "save to" instruction
                if "save as" not in task_description.lower() and "save to" not in task_description.lower():
                    # Add a "save as" instruction to the task
                    task_description = f"{task_description} (Save as '{filename}')"
                    
            # Use the create_file method from AgenticOllama
            result = await self.agentic_ollama.create_file(task_description)
            
            # Get the filename from the result
            filename = result.get('filename', 'unknown')
            
            # Format the result properly for task manager
            return {
                "success": True,
                "task_type": "file_creation",
                "result": {
                    "filename": filename,
                    "file_type": os.path.splitext(filename)[1] if filename != 'unknown' else '',
                    "content_preview": result.get('content_preview', ''),
                    "full_result": result
                },
                "message": f"Successfully created file: {filename}"
            }
        except Exception as e:
            logger.error(f"Error creating file: {str(e)}")
            return {
                "success": False,
                "task_type": "file_creation",
                "error": str(e),
                "message": f"Failed to create file: {str(e)}"
            }
    
    async def _handle_image_analysis(self, task_description: str) -> Dict[str, Any]:
        """
        Handle image analysis tasks.
        
        Args:
            task_description: Natural language description of the image analysis task
            
        Returns:
            Dict containing the image analysis results
        """
        try:
            # Use the analyze_image method from AgenticOllama
            result = await self.agentic_ollama.analyze_image(task_description)
            
            return {
                "success": True,
                "task_type": "image_analysis",
                "result": result,
                "message": "Successfully analyzed image"
            }
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {
                "success": False,
                "task_type": "image_analysis",
                "error": str(e),
                "message": f"Failed to analyze image: {str(e)}"
            }
    
    async def _handle_web_browsing_task(self, task_description: str) -> Dict[str, Any]:
        """
        Handle web browsing tasks.
        
        Args:
            task_description: Natural language description of the web browsing task
            
        Returns:
            Dict containing the web browsing results
        """
        try:
            # Use the browse_web method from AgenticOllama
            result = await self.agentic_ollama.browse_web(task_description)
            
            return {
                "success": True,
                "task_type": "web_browsing",
                "result": result,
                "message": "Successfully browsed the web"
            }
        except Exception as e:
            logger.error(f"Error browsing the web: {str(e)}")
            
            # If web browsing fails, try to handle it as a file creation task
            # This is a fallback mechanism for tasks that might be misclassified
            if "No URLs found" in str(e) or "Failed to extract URLs" in str(e):
                logger.info("Attempting to handle failed web browsing task as file creation task")
                return await self._handle_file_creation(task_description)
            
            return {
                "success": False,
                "task_type": "web_browsing",
                "error": str(e),
                "message": f"Failed to browse the web: {str(e)}"
            }
    
    async def _handle_general_task(self, task_description: str) -> Dict[str, Any]:
        """
        Handle general tasks.
        
        Args:
            task_description: Natural language description of the general task
            
        Returns:
            Dict containing the general task results
        """
        try:
            # Use the execute_task method from AgenticOllama
            result = await self.agentic_ollama.execute_task(task_description)
            
            return {
                "success": True,
                "task_type": "general",
                "result": result,
                "message": "Successfully executed task"
            }
        except Exception as e:
            logger.error(f"Error executing general task: {str(e)}")
            return {
                "success": False,
                "task_type": "general",
                "error": str(e),
                "message": f"Failed to execute task: {str(e)}"
            }

# Function to execute a task using the Agentic Assistant
async def execute_agentic_assistant_task(task: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a task using the Agentic Assistant.
    
    Args:
        task: The task description to execute
        model: The Ollama model to use (optional)
        
    Returns:
        Dict containing the execution results
    """
    try:
        # Initialize the Agentic Assistant
        assistant = AgenticAssistant(model)
        
        # Execute the task
        return await assistant.execute_task(task)
    
    except Exception as e:
        logger.error(f"Error handling task: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to execute task: {str(e)}"
        }

# Function to display task execution results
def display_agentic_assistant_result(result: Dict[str, Any]):
    """
    Display the results of a task execution.
    
    Args:
        result: The task execution result dictionary
    """
    if result.get("success", False):
        # Format the result based on the task type
        if result.get("task_type") == "file_creation":
            # Use the display_file_result function from fixed_file_handler.py
            display_file_result(result)
        elif result.get("task_type") == "image_analysis":
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            analysis_result = result.get("result", {})
            console.print(Panel(
                Markdown(analysis_result.get("analysis", "No analysis available")),
                title="Image Analysis",
                border_style="blue"
            ))
        elif result.get("task_type") == "web_browsing":
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            web_result = result.get("result", {})
            
            # Display the web browsing results
            if "summary" in web_result:
                console.print(Panel(
                    Markdown(web_result.get("summary", "No summary available")),
                    title="Web Browsing Summary",
                    border_style="blue"
                ))
            
            # Display the visited URLs
            if "visited_urls" in web_result and web_result["visited_urls"]:
                console.print("[bold]Visited URLs:[/bold]")
                for url in web_result["visited_urls"]:
                    console.print(f"- {url}")
        else:
            # General task result
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            
            # Display the task result
            task_result = result.get("result", {})
            if isinstance(task_result, dict) and "response" in task_result:
                console.print(Panel(
                    Markdown(task_result.get("response", "No response available")),
                    border_style="blue"
                ))
            elif isinstance(task_result, str):
                console.print(Panel(
                    Markdown(task_result),
                    border_style="blue"
                ))
            else:
                console.print(Panel(
                    Markdown(str(task_result)),
                    border_style="blue"
                ))
    else:
        # Display the error message
        console.print(f"[bold red]✗ {result.get('message', 'Task failed')}[/bold red]")
        
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")

# Function to enter the Agentic Assistant interactive mode
def agentic_assistant_mode(model: Optional[str] = None):
    """
    Enter the Agentic Assistant interactive mode.
    
    Args:
        model: The Ollama model to use (optional)
    """
    console.print("[bold]Welcome to the Agentic Assistant![/bold]")
    console.print("Type 'exit' or 'quit' to exit the assistant mode.")
    
    while True:
        # Get the task from the user
        task = console.input("\n[bold]What would you like me to do?[/bold] ")
        
        # Check if the user wants to exit
        if task.lower() in ["exit", "quit"]:
            console.print("[bold]Exiting Agentic Assistant mode.[/bold]")
            break
        
        # Execute the task
        result = asyncio.run(execute_agentic_assistant_task(task, model))
        
        # Display the result
        display_agentic_assistant_result(result)

# Main function
if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic Assistant")
    parser.add_argument("--model", type=str, help="The Ollama model to use")
    parser.add_argument("--task", type=str, help="The task to execute")
    
    args = parser.parse_args()
    
    if args.task:
        # Execute the task
        result = asyncio.run(execute_agentic_assistant_task(args.task, args.model))
        
        # Display the result
        display_agentic_assistant_result(result)
    else:
        # Enter the interactive mode
        agentic_assistant_mode(args.model)

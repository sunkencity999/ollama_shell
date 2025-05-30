#!/usr/bin/env python3
"""
Agentic Assistant for Ollama Shell

This module provides an integrated agentic assistant that can complete complex tasks
using natural language instructions. It leverages the existing AgenticOllama class
to perform various operations including file creation, analysis, and task execution.
"""

import os
import sys
import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agentic_assistant")

# Import the AgenticOllama class
from agentic_ollama import AgenticOllama

# Import Glama MCP integration
try:
    from glama_mcp_integration import handle_web_task
    GLAMA_MCP_AVAILABLE = True
    logger.info("Local web integration available. Web browsing features enabled.")
except ImportError:
    logger.warning("Local web integration not available. Web browsing features will be limited.")
    GLAMA_MCP_AVAILABLE = False

# Initialize console for rich output
console = Console()

class AgenticAssistant:
    """
    Agentic Assistant for Ollama Shell.
    Provides a user-friendly interface for executing complex tasks through natural language.
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the Agentic Assistant.
        
        Args:
            model: The Ollama model to use for task execution
        """
        self.agentic_ollama = AgenticOllama()
        self.model = model or self.agentic_ollama.model
        
        # Log initialization
        logger.info(f"Initialized Agentic Assistant with model: {self.model}")
    
    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a complex task based on natural language description.
        
        Args:
            task_description: Natural language description of the task to execute
            
        Returns:
            Dict containing the execution results
        """
        # Display task information
        console.print(f"[bold blue]Executing task:[/bold blue] {task_description}")
        
        # Determine the appropriate action based on the task description
        task_lower = task_description.lower()
        
        # File creation task
        if "create" in task_lower and ("file" in task_lower or "." in task_lower):
            return await self._handle_file_creation(task_description)
        
        # Image analysis task
        elif "analyze" in task_lower and any(ext in task_lower for ext in [".jpg", ".png", ".jpeg", ".gif", "image"]):
            return await self._handle_image_analysis(task_description)
        
        # Image search and download task
        elif ("find" in task_lower or "search" in task_lower or "get" in task_lower) and \
             ("image" in task_lower or "photo" in task_lower or "picture" in task_lower) and \
             ("save" in task_lower or "download" in task_lower or "folder" in task_lower or "directory" in task_lower):
            return await self._handle_image_search_task(task_description)
        
        # File organization task
        elif ("organize" in task_lower or "sort" in task_lower or "categorize" in task_lower) and \
             ("file" in task_lower or "files" in task_lower or "document" in task_lower or "documents" in task_lower) or \
             (("find" in task_lower) and ("file" in task_lower or "files" in task_lower) and \
             ("folder" in task_lower or "directory" in task_lower)):
            return await self._handle_file_organization(task_description)
            
        # File deletion task
        elif ("delete" in task_lower or "remove" in task_lower) and \
             ("file" in task_lower or "files" in task_lower or "image" in task_lower or "images" in task_lower or \
              "picture" in task_lower or "pictures" in task_lower or "photo" in task_lower or "photos" in task_lower):
            return await self._handle_file_deletion(task_description)
        
        # Web-related tasks (using Glama MCP)
        elif GLAMA_MCP_AVAILABLE and (
            # Standard web browsing patterns
            (("browse" in task_lower or "visit" in task_lower or "go to" in task_lower) and \
            ("website" in task_lower or "web" in task_lower or "url" in task_lower or "http" in task_lower)) or \
            # News/headlines gathering patterns
            (("headlines" in task_lower or "news" in task_lower) and ("gather" in task_lower or "collect" in task_lower)) or \
            # Information gathering with save to file
            (("gather" in task_lower or "collect" in task_lower or "get" in task_lower) and \
             ("information" in task_lower or "data" in task_lower or "websites" in task_lower or "about" in task_lower)) or \
            # Web search patterns
            (("search" in task_lower or "find" in task_lower or "look up" in task_lower or "research" in task_lower) and \
             ("web" in task_lower or "internet" in task_lower or "online" in task_lower or "information" in task_lower)) or \
            # File saving patterns (indicating web content gathering)
            ("save" in task_lower and (".txt" in task_lower or "file" in task_lower or "document" in task_lower))
        ):
            return await self._handle_web_browsing_task(task_description)
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
            # Use the create_file method from AgenticOllama
            result = await self.agentic_ollama.create_file(task_description)
            return {
                "success": True,
                "task_type": "file_creation",
                "result": result,
                "message": f"Successfully created file: {result.get('filename', 'unknown')}"
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
            task_description: Natural language description of the image to analyze
            
        Returns:
            Dict containing the image analysis results
        """
        try:
            # Extract image path from task description
            # This is a simple implementation - in practice, you might want to use regex or LLM to extract the path
            words = task_description.split()
            image_path = None
            for word in words:
                if any(word.lower().endswith(ext) for ext in [".jpg", ".png", ".jpeg", ".gif"]):
                    image_path = word
                    break
            
            if not image_path:
                return {
                    "success": False,
                    "task_type": "image_analysis",
                    "error": "Could not determine image path from task description",
                    "message": "Please specify the image file to analyze"
                }
            
            # Use the analyze_image method from AgenticOllama
            result = await self.agentic_ollama.analyze_image(image_path, task_description)
            return {
                "success": True,
                "task_type": "image_analysis",
                "result": result,
                "message": f"Successfully analyzed image: {image_path}"
            }
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {
                "success": False,
                "task_type": "image_analysis",
                "error": str(e),
                "message": f"Failed to analyze image: {str(e)}"
            }
    
    async def _handle_image_search_task(self, task_description: str) -> Dict[str, Any]:
        """
        Handle image search and download tasks.
        
        Args:
            task_description: Natural language description of the image search task
            
        Returns:
            Dict containing the image search results
        """
        try:
            # Use the AgenticOllama's image search handler
            result = await self.agentic_ollama._handle_image_search_task(task_description)
            
            # Extract the relevant information from the result
            if isinstance(result, dict) and result.get("success", False):
                return {
                    "success": True,
                    "task_type": "image_search",
                    "result": result.get("response", ""),
                    "message": "Image search completed successfully"
                }
            else:
                raise Exception("Image search failed: " + str(result.get("error", "Unknown error")))
        except Exception as e:
            logger.error(f"Error searching for images: {str(e)}")
            return {
                "success": False,
                "task_type": "image_search",
                "error": str(e),
                "message": f"Failed to search for images: {str(e)}"
            }
    
    async def _handle_file_organization(self, task_description: str) -> Dict[str, Any]:
        """
        Handle file organization tasks using the agentic_ollama module.
        
        Args:
            task_description: Natural language description of the file organization task
            
        Returns:
            Dict containing the file organization results
        """
        try:
            # Use the organize_files method from AgenticOllama
            result = await self.agentic_ollama.organize_files(task_description)
            
            # Extract the relevant information from the result
            if isinstance(result, dict) and result.get("success", False):
                return {
                    "success": True,
                    "task_type": "file_organization",
                    "result": result.get("summary", ""),
                    "message": "File organization completed successfully",
                    "categories": result.get("categories", []),
                    "files_found": result.get("files_found", 0),
                    "directory": result.get("directory", "")
                }
            else:
                raise Exception("File organization failed: " + str(result.get("error", "Unknown error")))
        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            return {
                "success": False,
                "task_type": "file_organization",
                "error": str(e),
                "message": f"Failed to organize files: {str(e)}"
            }
            
    async def _handle_file_deletion(self, task_description: str) -> Dict[str, Any]:
        """
        Handle file deletion tasks using the agentic_ollama module.
        
        Args:
            task_description: Natural language description of the file deletion task
            
        Returns:
            Dict containing the file deletion results
        """
        try:
            # Use the delete_files method from AgenticOllama
            result = await self.agentic_ollama.delete_files(task_description)
            
            # Extract the relevant information from the result
            if isinstance(result, dict) and result.get("success", False):
                return {
                    "success": True,
                    "task_type": "file_deletion",
                    "result": result.get("summary", ""),
                    "message": "File deletion completed successfully",
                    "files_deleted": result.get("files_deleted", 0),
                    "directory": result.get("directory", "")
                }
            else:
                raise Exception("File deletion failed: " + str(result.get("error", "Unknown error")))
        except Exception as e:
            logger.error(f"Error deleting files: {str(e)}")
            return {
                "success": False,
                "task_type": "file_deletion",
                "error": str(e),
                "message": f"Failed to delete files: {str(e)}"
            }
    

    
    async def _handle_web_browsing_task(self, task_description: str) -> Dict[str, Any]:
        """
        Handle web browsing tasks using the Glama MCP integration.
        
        Args:
            task_description: Natural language description of the web browsing task
            
        Returns:
            Dict containing the web browsing results
        """
        try:
            if not GLAMA_MCP_AVAILABLE:
                raise Exception("Local web integration is not available. Cannot perform web browsing tasks.")
            
            # Extract filename from task description if specified
            import re
            filename_match = re.search(r'[\"\'](.*?\.txt)[\"\']\.?', task_description)
            custom_filename = filename_match.group(1) if filename_match else None
            
            # Use the handle_web_task function from the local web integration
            # Pass the custom filename if found
            if custom_filename:
                # Modify task description to ensure the filename is properly passed to the web integration
                task_with_filename = f"{task_description} (Save as {custom_filename})"
                result = await handle_web_task(task_with_filename)
            else:
                result = await handle_web_task(task_description)
            
            # Extract the relevant information from the result
            if isinstance(result, dict) and result.get("success", False):
                # Handle different types of web tasks
                task_type = result.get("task_type", "web_browsing")
                
                # Handle different content types (news, gaming, tech, fishing, etc.)
                if "headlines" in task_type or "information" in task_type:
                    # Determine if this is a headline request or general information request
                    is_headline_request = ("headlines" in task_type or 
                                         "headlines" in task_description.lower() or 
                                         "news" in task_description.lower() or
                                         "latest" in task_description.lower())
                    
                    # Explicitly check for information gathering patterns that should NOT be treated as headlines
                    if ("information about" in task_description.lower() or
                        "information on" in task_description.lower() or
                        "tips" in task_description.lower() or
                        "guide" in task_description.lower() or
                        "learn about" in task_description.lower() or
                        "research" in task_description.lower()):
                        is_headline_request = False
                    
                    # Get sample content based on request type
                    if is_headline_request:
                        sample_content = result.get("sample_headlines", result.get("headlines", [])[:3])
                        content_label = "Sample headlines"
                    else:
                        sample_content = result.get("sample_information", result.get("information", [])[:3])
                        if not sample_content and result.get("headlines"):
                            # Fall back to headlines if no specific information was extracted
                            sample_content = result.get("headlines", [])[:3]
                        content_label = "Sample information"
                    
                    sample_text = " ".join(sample_content)
                    
                    # Extract the content type from task_type (e.g., "gaming_headlines" -> "Gaming", "fishing_information" -> "Fishing")
                    if "_" in task_type:
                        content_type = task_type.split("_")[0].title()
                    else:
                        # If no underscore, use a default based on the task description
                        content_type = "Information"
                        
                        # Try to extract content type from the task description using a more dynamic approach
                        # Look for nouns that appear before keywords like "information", "websites", "about", etc.
                        topic_indicators = ["about", "on", "regarding", "for", "related to"]
                        for indicator in topic_indicators:
                            pattern = rf"(?:information|data|websites|research|headlines)\s+{indicator}\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b"
                            topic_match = re.search(pattern, task_description.lower())
                            if topic_match:
                                content_type = topic_match.group(1).title()
                                break
                                
                        # If no match found with the above pattern, try to find the main subject
                        if content_type == "Information":
                            # Look for nouns that appear before "websites" or after "gather"
                            subject_patterns = [
                                r"gather\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:information|data)",
                                r"([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+(?:websites|information|data)",
                                r"(?:research|find|get)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)"
                            ]
                            
                            for pattern in subject_patterns:
                                subject_match = re.search(pattern, task_description.lower())
                                if subject_match:
                                    subject = subject_match.group(1)
                                    # Filter out common stop words
                                    stop_words = ["the", "some", "any", "more", "new", "recent", "popular", "good", "best"]
                                    if subject not in stop_words:
                                        content_type = subject.title()
                                        break
                    
                    # Use the actual filename from the result
                    actual_filename = result.get('filename', 'unknown.txt')
                    
                    # Create appropriate success message based on content type
                    if is_headline_request:
                        success_message = f"{content_type} Headlines gathered successfully"
                        result_text = f"Headlines gathered and saved to {actual_filename}\n\n{content_label}: {sample_text}"
                    else:
                        success_message = f"{content_type} Information gathered successfully"
                        result_text = f"Information gathered and saved to {actual_filename}\n\n{content_label}: {sample_text}"
                    
                    return {
                        "success": True,
                        "task_type": task_type,
                        "result": result_text,
                        "message": success_message,
                        "headlines": result.get("headlines", []),
                        "information": result.get("information", []),
                        "filename": actual_filename
                    }
                else:
                    return {
                        "success": True,
                        "task_type": task_type,
                        "result": result.get("result", ""),
                        "message": "Web browsing completed successfully",
                        "url": result.get("url", "")
                    }
            else:
                raise Exception("Web browsing failed: " + str(result.get("error", "Unknown error")))
        except Exception as e:
            logger.error(f"Error browsing web: {str(e)}")
            return {
                "success": False,
                "task_type": "web_browsing",
                "error": str(e),
                "message": f"Failed to browse web: {str(e)}"
            }
    
    async def _handle_general_task(self, task_description: str) -> Dict[str, Any]:
        """
        Handle general task execution.
        
        Args:
            task_description: Natural language description of the task to execute
            
        Returns:
            Dict containing the task execution results
        """
        try:
            # Create a system prompt for the task
            system_prompt = """You are an agentic assistant that helps users complete tasks. 
            Your goal is to understand the user's request and provide a detailed, step-by-step 
            solution to accomplish their task. If the task involves code, provide complete, 
            working code examples. If the task involves analysis, provide a thorough analysis 
            with clear explanations. Be helpful, accurate, and comprehensive in your response."""
            
            # Use the _generate_completion method from AgenticOllama to process the task
            completion_result = await self.agentic_ollama._generate_completion(
                f"User request: {task_description}",
                system_prompt
            )
            
            if completion_result.get("success", False):
                return {
                    "success": True,
                    "task_type": "general_task",
                    "result": completion_result.get("result", ""),
                    "message": "Task executed successfully"
                }
            else:
                raise Exception(completion_result.get("error", "Unknown error"))
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            return {
                "success": False,
                "task_type": "general_task",
                "error": str(e),
                "message": f"Failed to execute task: {str(e)}"
            }

async def agentic_assistant_mode(model: Optional[str] = None):
    """
    Enter interactive Agentic Assistant mode.
    
    Args:
        model: The Ollama model to use for task execution
    """
    try:
        # Initialize the Agentic Assistant
        assistant = AgenticAssistant(model)
        
        # Display welcome message
        console.print(Panel(
            "[bold green]Agentic Assistant Mode[/bold green]\n\n"
            "Enter natural language tasks to execute, or type 'exit' to return to the main menu.\n"
            "Examples:\n"
            "  - Create a Python script that calculates prime numbers\n"
            "  - Analyze the image sunset.jpg and describe what you see\n"
            "  - Help me write a regular expression to match email addresses",
            title="Welcome to Agentic Assistant",
            border_style="green"
        ))
        
        # Main interaction loop
        while True:
            # Get user input
            task = Prompt.ask("\n[bold cyan]Enter task[/bold cyan]")
            
            # Check for exit command
            if task.lower() in ["exit", "quit", "back"]:
                console.print("[yellow]Exiting Agentic Assistant mode...[/yellow]")
                break
            
            # Execute the task
            result = await assistant.execute_task(task)
            
            # Display the result
            if result.get("success", False):
                # Format the result based on the task type
                if result.get("task_type") == "file_creation":
                    file_result = result.get("result", {})
                    console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
                    console.print(f"[bold]File:[/bold] {file_result.get('filename', 'unknown')}")
                    console.print(f"[bold]Type:[/bold] {file_result.get('file_type', 'unknown')}")
                    if "content_preview" in file_result:
                        console.print("[bold]Content Preview:[/bold]")
                        console.print(Panel(file_result.get("content_preview", ""), border_style="blue"))
                elif result.get("task_type") == "image_analysis":
                    console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
                    analysis_result = result.get("result", {})
                    console.print(Panel(
                        Markdown(analysis_result.get("analysis", "No analysis available")),
                        title="Image Analysis",
                        border_style="blue"
                    ))
                else:
                    console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
                    task_result = result.get("result", "")
                    console.print(Panel(
                        Markdown(task_result),
                        title="Task Result",
                        border_style="blue"
                    ))
            else:
                # Display error message
                console.print(f"[bold red]✗ {result.get('message', 'Task failed')}[/bold red]")
                if "error" in result:
                    console.print(f"[red]Error: {result['error']}[/red]")
    
    except Exception as e:
        console.print(f"[bold red]Error in Agentic Assistant mode: {str(e)}[/bold red]")
        logger.error(f"Error in Agentic Assistant mode: {str(e)}")
    
    finally:
        console.print("[yellow]Returned to main menu[/yellow]")

# Function to handle a single task execution
async def handle_agentic_assistant_task(task: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle a single task execution request.
    
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
            file_result = result.get("result", {})
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            console.print(f"[bold]File:[/bold] {file_result.get('filename', 'unknown')}")
            console.print(f"[bold]Type:[/bold] {file_result.get('file_type', 'unknown')}")
            if "content_preview" in file_result:
                console.print("[bold]Content Preview:[/bold]")
                console.print(Panel(file_result.get("content_preview", ""), border_style="blue"))
        elif result.get("task_type") == "image_analysis":
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            analysis_result = result.get("result", {})
            console.print(Panel(
                Markdown(analysis_result.get("analysis", "No analysis available")),
                title="Image Analysis",
                border_style="blue"
            ))
        elif result.get("task_type", "").startswith("web_") or "headlines" in result.get("task_type", "") or "information" in result.get("task_type", ""):
            # Handle web browsing tasks
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            
            # Display the result with proper formatting
            task_result = result.get("result", "")
            
            # If we have a filename, display it prominently
            if "filename" in result:
                console.print(f"[bold]File saved:[/bold] {result['filename']}")
                
                # If we have headlines or information, display them
                headlines = result.get("headlines", [])
                information = result.get("information", [])
                sample_headlines = result.get("sample_headlines", [])
                sample_information = result.get("sample_information", [])
                
                if sample_headlines:
                    sample_text = "\n- " + "\n- ".join(sample_headlines[:3])
                    console.print(f"[bold]Sample content:[/bold]{sample_text}")
                elif headlines:
                    sample_text = "\n- " + "\n- ".join(headlines[:3])
                    console.print(f"[bold]Sample headlines:[/bold]{sample_text}")
                elif sample_information:
                    # Format sample information better
                    sample_text = "\n- " + "\n- ".join(sample_information[:3])
                    console.print(f"[bold]Sample information:[/bold]{sample_text}")
                elif information:
                    sample_text = "\n- " + "\n- ".join(information[:3])
                    console.print(f"[bold]Sample information:[/bold]{sample_text}")
            
            # Display the full result if available
            if task_result:
                console.print(Panel(
                    Markdown(task_result),
                    title="Task Result",
                    border_style="blue"
                ))
        else:
            console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
            task_result = result.get("result", "")
            console.print(Panel(
                Markdown(task_result),
                title="Task Result",
                border_style="blue"
            ))
    else:
        # Display error message
        console.print(f"[bold red]✗ {result.get('message', 'Task failed')}[/bold red]")
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")

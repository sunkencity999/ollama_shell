#!/usr/bin/env python3
"""
Enhanced Agentic Assistant for Ollama Shell

This module extends the original AgenticAssistant with task management capabilities
for handling complex, multi-step tasks. It integrates the TaskManager, TaskPlanner,
and TaskExecutor to break down complex requests into manageable subtasks.
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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.syntax import Syntax

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agentic_assistant_enhanced")

# Import the original AgenticAssistant
from agentic_assistant import AgenticAssistant, console

# Import the task management system
from task_manager import TaskManager, TaskPlanner, TaskExecutor, TaskStatus

class EnhancedAgenticAssistant(AgenticAssistant):
    """
    Enhanced Agentic Assistant with task management capabilities.
    Extends the original AgenticAssistant to handle complex, multi-step tasks.
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the Enhanced Agentic Assistant.
        
        Args:
            model: The Ollama model to use for task execution
        """
        super().__init__(model)
        
        # Initialize task management components
        self.task_manager = TaskManager()
        self.task_planner = TaskPlanner(self.agentic_ollama)
        self.task_executor = TaskExecutor(self, self.task_manager)
        
        logger.info("Initialized EnhancedAgenticAssistant with task management capabilities")
    
    async def execute_complex_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a complex, multi-step task by breaking it down into subtasks.
        
        Args:
            task_description: Natural language description of the complex task
            
        Returns:
            Dict containing the execution results
        """
        console.print(f"[bold blue]Analyzing complex task:[/bold blue] {task_description}")
        
        try:
            # Step 1: Plan the task
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Planning task...[/bold blue]"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Planning", total=1)
                
                # Plan the task using the TaskPlanner
                workflow_id = await self.task_planner.plan_task(task_description)
                progress.update(task, completed=1)
            
            # Step 2: Display the task plan
            self._display_task_plan(workflow_id)
            
            # Step 3: Execute the workflow
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Executing tasks...[/bold blue]"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Executing", total=100)
                
                # Start the execution
                execution_task = asyncio.create_task(self.task_executor.execute_workflow(workflow_id))
                
                # Update progress while execution is running
                while not execution_task.done():
                    # Get current workflow status
                    status = self.task_manager.get_workflow_status()
                    progress_percentage = status["progress_percentage"]
                    
                    # Update progress bar
                    progress.update(task, completed=progress_percentage)
                    
                    # Wait a bit before checking again
                    await asyncio.sleep(0.5)
                
                # Get the final result
                result = await execution_task
                progress.update(task, completed=100)
            
            # Step 4: Display the execution results
            return self._display_execution_results(workflow_id)
            
        except Exception as e:
            logger.error(f"Error executing complex task: {str(e)}")
            return {
                "success": False,
                "task_type": "complex_task",
                "error": str(e),
                "message": f"Failed to execute complex task: {str(e)}"
            }
    
    def _display_task_plan(self, workflow_id: str) -> None:
        """
        Display the task plan to the user.
        
        Args:
            workflow_id: ID of the workflow to display
        """
        # Load the workflow
        self.task_manager.load_workflow(workflow_id)
        
        # Get all tasks
        tasks = self.task_manager.get_all_tasks()
        
        # Create a table to display the task plan
        table = Table(title="Task Execution Plan")
        table.add_column("Step", style="cyan")
        table.add_column("Task", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Dependencies", style="magenta")
        
        # Add tasks to the table
        for i, task in enumerate(tasks, 1):
            # Format dependencies
            if task.dependencies:
                # Map dependency IDs to step numbers for better readability
                dep_steps = []
                for dep_id in task.dependencies:
                    # Find the index of the dependency task
                    for j, t in enumerate(tasks, 1):
                        if t.id == dep_id:
                            dep_steps.append(str(j))
                            break
                
                dependencies = ", ".join(dep_steps)
            else:
                dependencies = "None"
            
            table.add_row(
                str(i),
                task.description[:50] + ("..." if len(task.description) > 50 else ""),
                task.task_type.replace("_", " ").title(),
                dependencies
            )
        
        # Display the table
        console.print(Panel(table, title="Task Execution Plan", border_style="blue"))
        console.print("[bold green]Starting task execution...[/bold green]")
    
    def _is_direct_file_creation_task(self, task_description: str) -> bool:
        """
        Determine if a task is a direct file creation task that should be handled directly.
        
        Args:
            task_description: Description of the task
            
        Returns:
            True if the task is a direct file creation task, False otherwise
        """
        # Pattern 1: Create a file/document with...
        pattern1 = r"create\s+(?:a|an)\s+(?:file|document|text|story|poem|essay|article|report|note)\s+(?:with|about|for|containing)"
        if re.search(pattern1, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 2: Write a story/poem/essay...
        pattern2 = r"write\s+(?:a|an)\s+(?:story|poem|essay|article|report|note|text|document)"
        if re.search(pattern2, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 3: Save as filename...
        pattern3 = r"save\s+(?:it|this|the\s+file|the\s+document)\s+as\s+([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)"
        if re.search(pattern3, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 4: Create a file named/called...
        pattern4 = r"create\s+(?:a|an)\s+(?:file|document)\s+(?:named|called)"
        if re.search(pattern4, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 5: Save to folder as filename...
        pattern5 = r"save\s+(?:it|this)?\s+to\s+(?:my\s+)?(?:[\w\s]+\s+)?folder\s+as\s+"
        if re.search(pattern5, task_description, re.IGNORECASE):
            logger.info(f"Detected direct file creation task with folder path: '{task_description}'. Handling directly.")
            return True
        
        # Pattern 6: Look for quoted filenames
        pattern6 = r'["\']+[\w\-\.\s]+\.[\w]+["\']+' 
        if re.search(pattern6, task_description, re.IGNORECASE) and ("create" in task_description.lower() or "write" in task_description.lower() or "save" in task_description.lower()):
            logger.info(f"Detected direct file creation task with quoted filename: '{task_description}'. Handling directly.")
            return True
        
        # Fallback pattern: If it contains create/write/save and doesn't look like a web search
        web_patterns = [r"search", r"find", r"look\s+up", r"browse", r"internet", r"web"]
        has_web_term = any(re.search(p, task_description, re.IGNORECASE) for p in web_patterns)
        
        if not has_web_term and ("create" in task_description.lower() or "write" in task_description.lower() or "save" in task_description.lower()):
            logger.info(f"Detected simple file creation task: '{task_description}'. Using standard execution.")
            return True
        
        return False
    
    async def _handle_file_creation(self, task_description: str) -> Dict[str, Any]:
        """
        Handle file creation tasks directly, bypassing the task management system.
        This method overrides the parent class method to add enhanced functionality.
        
        Args:
            task_description: Description of the file creation task
            
        Returns:
            Dict containing the result of the file creation operation
        """
        logger.info(f"Handling file creation task directly: {task_description}")
        
        try:
            # Extract the filename from the task description using the enhanced method
            filename = self._extract_filename(task_description)
            result = await self.agentic_ollama.create_file(task_description, filename)
            
            # Return a properly formatted result
            success = result.get("success", False)
            message = result.get("message", "File creation completed")
            
            # Extract the result data
            result_data = {}
            if success and "result" in result and isinstance(result["result"], dict):
                result_data = {
                    "filename": result["result"].get("filename", "Unknown"),
                    "file_type": result["result"].get("file_type", "txt"),
                    "content_preview": result["result"].get("content_preview", "No preview available")
                }
            
            return {
                "success": success,
                "task_type": "file_creation",
                "result": result_data,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error handling file creation task: {str(e)}")
            return {
                "success": False,
                "task_type": "file_creation",
                "error": str(e),
                "message": f"Failed to create file: {str(e)}"
            }
    
    def _extract_filename(self, task_description: str) -> str:
        """
        Extract the filename from a task description using multiple regex patterns.
        If no filename is found, generate a default one based on content type.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Extracted or generated filename
        """
        logger.info(f"Extracting filename from: {task_description}")
        
        # Pattern 1: "save it to my [folder] as [filename]" - handles paths with quotes
        save_path_match = re.search(r'save\s+(?:it|this|the\s+\w+)?\s+(?:to|in)\s+(?:my\s+)?(?:[\w\s]+\s+)?folder\s+as\s+["\']+([\w\-\.\s]+\.\w+)["\']+', task_description, re.IGNORECASE)
        if save_path_match:
            filename = save_path_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 1 (path with quotes): {filename}")
            return filename
        
        # Pattern 2: "save it to/as/in [filename]" - standard pattern
        save_as_match = re.search(r'save\s+(?:it|this|the\s+\w+)\s+(?:to|as|in)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
        if save_as_match:
            filename = save_as_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 2 (standard save as): {filename}")
            return filename
        
        # Pattern 3: "save to/as/in [filename]" - shorter variant
        save_to_match = re.search(r'save\s+(?:to|as|in)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
        if save_to_match:
            filename = save_to_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 3 (short save to): {filename}")
            return filename
        
        # Pattern 4: "create/write a [content] and save it as [filename]" - compound action
        create_save_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:and|&)\s+save\s+(?:it|this)\s+(?:to|as|in)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
        if create_save_match:
            filename = create_save_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 4 (compound action): {filename}")
            return filename
        
        # Pattern 5: "create/write a [content] called/named [filename]" - named content
        called_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:called|named)\s+["\']+([\w\-\.\s]+\.\w+)["\']+', task_description, re.IGNORECASE)
        if called_match:
            filename = called_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 5 (named content): {filename}")
            return filename
        
        # Pattern 6: "create/write [filename]" - direct file creation
        create_file_match = re.search(r'(?:create|write)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
        if create_file_match:
            filename = create_file_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 6 (direct file): {filename}")
            return filename
        
        # Pattern 7: Look for any quoted text ending with a file extension
        quoted_filename_match = re.search(r'["\']+([\w\-\.\s]+\.\w+)["\']+', task_description, re.IGNORECASE)
        if quoted_filename_match:
            filename = quoted_filename_match.group(1).strip()
            logger.info(f"Extracted filename using pattern 7 (quoted text): {filename}")
            return filename
        
        # If no filename is found, generate a default one based on content type
        logger.info(f"No filename found in: {task_description}")
        content_type = self._detect_content_type(task_description)
        default_filename = f"{content_type}.txt"
        logger.info(f"No filename found, using default: {default_filename}")
        return default_filename
    
    def _detect_content_type(self, task_description: str) -> str:
        """
        Detect the content type from the task description.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Detected content type (e.g., "essay", "story", "poem", etc.)
        """
        # Map of content types to their keywords
        content_types = {
            "essay": ["essay", "paper", "article", "composition"],
            "story": ["story", "tale", "narrative", "fiction"],
            "poem": ["poem", "poetry", "verse", "rhyme"],
            "report": ["report", "analysis", "summary", "review"],
            "letter": ["letter", "email", "correspondence"],
            "script": ["script", "screenplay", "dialogue"],
            "code": ["code", "program", "script", "function"],
            "recipe": ["recipe", "instructions", "steps", "ingredients"],
            "note": ["note", "memo", "reminder"],
            "document": ["document", "doc", "file"],
        }
        
        # Check for each content type
        for content_type, keywords in content_types.items():
            for keyword in keywords:
                if keyword in task_description.lower():
                    return content_type
        
        # Default to "document" if no content type is detected
        return "document"
    
    def _display_execution_results(self, workflow_id: str) -> Dict[str, Any]:
        """
        Display the execution results to the user.
        
        Args:
            workflow_id: ID of the workflow to display
            
        Returns:
            Dict containing the execution results
        """
        # Load the workflow
        self.task_manager.load_workflow(workflow_id)
        
        # Get all tasks
        tasks = self.task_manager.get_all_tasks()
        
        # Get workflow status
        status = self.task_manager.get_workflow_status()
        
        # Create a table to display the results
        table = Table(title="Task Execution Results")
        table.add_column("Step", style="cyan")
        table.add_column("Task", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Result", style="magenta")
        
        # Track successful tasks and their artifacts
        successful_tasks = []
        all_artifacts = {}
        
        # Add tasks to the table
        for i, task in enumerate(tasks, 1):
            # Format status
            status_str = task.status.value.upper()
            status_style = {
                TaskStatus.COMPLETED.value: "[bold green]",
                TaskStatus.FAILED.value: "[bold red]",
                TaskStatus.IN_PROGRESS.value: "[bold yellow]",
                TaskStatus.PENDING.value: "[bold blue]",
                TaskStatus.BLOCKED.value: "[bold magenta]"
            }.get(task.status.value, "")
            
            # Format result
            if task.result:
                if task.result.success:
                    result_str = "Success"
                    successful_tasks.append(task)
                    
                    # Collect artifacts
                    for key, value in task.result.artifacts.items():
                        if key != "full_result":  # Skip the full result
                            all_artifacts[f"{task.task_type}_{key}"] = value
                else:
                    result_str = f"Error: {task.result.error}"
            else:
                result_str = "No result"
            
            table.add_row(
                str(i),
                task.description[:50] + ("..." if len(task.description) > 50 else ""),
                f"{status_style}{status_str}[/]",
                result_str
            )
        
        # Display the table
        console.print(Panel(table, title="Task Execution Results", border_style="blue"))
        
        # Determine overall success
        overall_success = status["failed_tasks"] == 0 and status["completed_tasks"] > 0
        
        # Prepare summary message
        if overall_success:
            message = f"Successfully completed all {status['completed_tasks']} tasks."
        elif status["completed_tasks"] > 0:
            message = f"Partially completed {status['completed_tasks']} out of {status['total_tasks']} tasks. {status['failed_tasks']} tasks failed."
        else:
            message = f"Failed to complete any tasks. All {status['total_tasks']} tasks failed."
        
        # Display artifacts from successful tasks
        if successful_tasks:
            console.print("[bold blue]Task Artifacts:[/bold blue]")
            
            # Track if we've already displayed a created file message
            displayed_file = False
            
            for task in successful_tasks:
                if task.result and task.result.artifacts:
                    # Display relevant artifacts based on task type
                    if task.task_type == "file_creation" and "filename" in task.result.artifacts:
                        filename = task.result.artifacts["filename"]
                        if filename:
                            console.print(f"[green]Created file:[/green] {filename}")
                            displayed_file = True
                            
                            # Show content preview if available
                            if "content_preview" in task.result.artifacts and task.result.artifacts["content_preview"]:
                                preview = task.result.artifacts["content_preview"]
                                if isinstance(preview, str) and preview.strip():
                                    console.print("[yellow]Content preview:[/yellow]")
                                    console.print(f"{preview[:200]}..." if len(preview) > 200 else preview)
                    
                    elif task.task_type == "web_browsing" and "filename" in task.result.artifacts:
                        filename = task.result.artifacts["filename"]
                        if filename and not displayed_file:  # Only show if we haven't already displayed a file
                            console.print(f"[green]Saved web content to:[/green] {filename}")
                            displayed_file = True
                        
                        # Show sample headlines if available
                        if "headlines" in task.result.artifacts and task.result.artifacts["headlines"]:
                            console.print("[yellow]Sample headlines:[/yellow]")
                            for headline in task.result.artifacts["headlines"][:3]:
                                console.print(f"- {headline}")
                    
                    elif task.task_type == "image_analysis" and "analysis" in task.result.artifacts:
                        analysis = task.result.artifacts["analysis"]
                        console.print(f"[green]Image analysis:[/green] {analysis[:100]}...")
        
        # Return the overall result
        return {
            "success": overall_success,
            "task_type": "complex_task",
            "result": {
                "workflow_id": workflow_id,
                "completed_tasks": status["completed_tasks"],
                "failed_tasks": status["failed_tasks"],
                "total_tasks": status["total_tasks"],
                "artifacts": all_artifacts
            },
            "message": message
        }
    
    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Override the original execute_task method to handle both simple and complex tasks.
        
        Args:
            task_description: Natural language description of the task to execute
            
        Returns:
            Dict containing the execution results
        """
        # Check if this is a complex task that should be broken down
        task_lower = task_description.lower()
        
        # First, check if this is a direct file creation task
        # These patterns strongly indicate a file creation task
        direct_file_creation_patterns = [
            "create a poem", "write a poem", "save a poem",
            "create a story", "write a story", "save a story",
            "create a file", "write a file", "save a file",
            "create a text", "write a text", "save a text",
            "create a document", "write a document", "save a document",
            "create an essay", "write an essay", "save an essay",
            "create a report", "write a report", "save a report"
        ]
        
        # Check for direct file creation patterns
        is_direct_file_creation = any(pattern in task_lower for pattern in direct_file_creation_patterns)
        
        # If it's a direct file creation task, handle it directly without task management
        if is_direct_file_creation:
            logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
            # Use the file creation handler from the parent class
            return await self._handle_file_creation(task_description)
        
        # Indicators of complex tasks
        complex_task_indicators = [
            # Multiple steps or actions
            "and then", "after that", "followed by", "next", "finally",
            # Multiple objectives
            "and also", "additionally", "as well as", "plus",
            # Complex research tasks
            "research and", "find information and", "gather data and",
            # Complex creation tasks
            "compile information",
            # Explicit multi-step requests
            "multi-step", "multiple steps", "several steps"
        ]
        
        # Check for complex task indicators
        is_complex_task = any(indicator in task_lower for indicator in complex_task_indicators)
        
        # Also check for multiple action verbs as an indicator of complexity
        action_verbs = ["find", "search", "analyze", "organize", "delete", "browse", "visit", 
                       "gather", "collect", "download", "compile", "summarize"]
        
        # Count action verbs (excluding create/write/save which are handled by direct file creation)
        verb_count = sum(1 for verb in action_verbs if verb in task_lower)
        
        is_complex_task = is_complex_task or verb_count >= 2
        
        # If it's a complex task, use the task management system
        if is_complex_task:
            logger.info(f"Detected complex task: '{task_description}'. Using task management system.")
            return await self.execute_complex_task(task_description)
        else:
            # For simple tasks, use the original implementation
            logger.info(f"Detected simple task: '{task_description}'. Using standard execution.")
            return await super().execute_task(task_description)

async def enhanced_agentic_assistant_mode(model: Optional[str] = None):
    """
    Enter interactive Enhanced Agentic Assistant mode.
    
    Args:
        model: The Ollama model to use for task execution
    """
    console.print(Panel(
        "[bold green]Enhanced Agentic Assistant Mode[/bold green]\n\n"
        "This assistant can help you with various tasks including:\n"
        "- Creating files with specific content\n"
        "- Analyzing images\n"
        "- Organizing files\n"
        "- Browsing websites and gathering information\n"
        "- Executing complex, multi-step tasks\n\n"
        "Type 'exit' or 'quit' to leave assistant mode.",
        title="Ollama Shell",
        border_style="blue"
    ))
    
    # Initialize the enhanced assistant
    assistant = EnhancedAgenticAssistant(model)
    
    while True:
        # Get user input
        task = Prompt.ask("[bold blue]What would you like me to do?[/bold blue]")
        
        # Check for exit command
        if task.lower() in ["exit", "quit", "bye", "goodbye"]:
            console.print("[bold green]Exiting Enhanced Agentic Assistant mode. Goodbye![/bold green]")
            break
        
        try:
            # Execute the task
            result = await assistant.execute_task(task)
            
            # Display the result
            display_agentic_assistant_result(result)
            
        except Exception as e:
            console.print(f"[bold red]Error executing task:[/bold red] {str(e)}")

def display_agentic_assistant_result(result: Dict[str, Any]):
    """
    Display the results of a task execution.
    
    Args:
        result: The task execution result dictionary
    """
    # Import from the original module to ensure consistent display
    from agentic_assistant import display_agentic_assistant_result as original_display
    
    # Use the original display function
    original_display(result)

async def handle_enhanced_agentic_assistant_task(task: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle a single task execution request using the enhanced assistant.
    
    Args:
        task: The task description to execute
        model: The Ollama model to use (optional)
        
    Returns:
        Dict containing the execution results
    """
    try:
        # Initialize the enhanced assistant
        assistant = EnhancedAgenticAssistant(model)
        
        # Execute the task
        return await assistant.execute_task(task)
    
    except Exception as e:
        logger.error(f"Error handling task: {str(e)}")
        return {
            "success": False,
            "task_type": "unknown",
            "error": str(e),
            "message": f"Failed to execute task: {str(e)}"
        }

if __name__ == "__main__":
    # Check if a task was provided as an argument
    if len(sys.argv) > 1:
        # Get the task from command line arguments
        task = " ".join(sys.argv[1:])
        
        # Execute the task
        result = asyncio.run(handle_enhanced_agentic_assistant_task(task))
        
        # Display the result
        display_agentic_assistant_result(result)
    else:
        # Enter interactive mode
        asyncio.run(enhanced_agentic_assistant_mode())

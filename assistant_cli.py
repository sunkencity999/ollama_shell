#!/usr/bin/env python3
"""
Command-line interface for the Enhanced Agentic Assistant

This module provides a command-line interface for interacting with the
Enhanced Agentic Assistant, allowing users to execute tasks, view task history,
and manage workflows.
"""

import os
import sys
import json
import asyncio
import argparse
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.syntax import Syntax

# Import the enhanced assistant
from agentic_assistant_enhanced import (
    EnhancedAgenticAssistant, 
    display_agentic_assistant_result,
    handle_enhanced_agentic_assistant_task
)

# Import task management components
from task_manager import TaskManager, TaskStatus

# Initialize console for rich output
console = Console()

async def execute_task(task: str, model: Optional[str] = None) -> None:
    """
    Execute a task using the Enhanced Agentic Assistant.
    
    Args:
        task: The task description to execute
        model: The Ollama model to use (optional)
    """
    console.print(f"[bold blue]Executing task:[/bold blue] {task}")
    
    # Execute the task
    result = await handle_enhanced_agentic_assistant_task(task, model)
    
    # Display the result
    display_agentic_assistant_result(result)

async def list_workflows() -> None:
    """
    List all saved workflows.
    """
    task_manager = TaskManager()
    workflows_dir = task_manager.storage_path
    
    if not os.path.exists(workflows_dir):
        console.print("[bold yellow]No workflows found.[/bold yellow]")
        return
    
    # Get all workflow directories
    workflow_dirs = [d for d in os.listdir(workflows_dir) 
                    if os.path.isdir(os.path.join(workflows_dir, d))]
    
    if not workflow_dirs:
        console.print("[bold yellow]No workflows found.[/bold yellow]")
        return
    
    # Create a table to display workflows
    table = Table(title="Saved Workflows")
    table.add_column("ID", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Status", style="magenta")
    
    # Add workflows to the table
    for workflow_id in workflow_dirs:
        workflow_path = os.path.join(workflows_dir, workflow_id)
        workflow_file = os.path.join(workflow_path, "workflow.json")
        
        if os.path.exists(workflow_file):
            try:
                with open(workflow_file, "r") as f:
                    workflow_data = json.load(f)
                
                # Get workflow information
                description = workflow_data.get("description", "Unknown")
                created_at = workflow_data.get("created_at", 0)
                status = workflow_data.get("status", "unknown")
                
                # Format created_at as a date string
                import datetime
                created_str = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
                
                table.add_row(
                    workflow_id[:8] + "...",  # Show only first 8 characters of ID
                    description[:50] + ("..." if len(description) > 50 else ""),
                    created_str,
                    status.upper()
                )
            except Exception as e:
                console.print(f"[bold red]Error reading workflow {workflow_id}:[/bold red] {str(e)}")
    
    # Display the table
    console.print(table)

async def view_workflow(workflow_id: str) -> None:
    """
    View details of a specific workflow.
    
    Args:
        workflow_id: ID of the workflow to view
    """
    task_manager = TaskManager()
    
    # Try to load the workflow
    if not task_manager.load_workflow(workflow_id):
        console.print(f"[bold red]Workflow {workflow_id} not found.[/bold red]")
        return
    
    # Get workflow status
    status = task_manager.get_workflow_status()
    
    # Get all tasks
    tasks = task_manager.get_all_tasks()
    
    # Display workflow information
    console.print(Panel(
        f"[bold blue]Workflow ID:[/bold blue] {workflow_id}\n"
        f"[bold blue]Total Tasks:[/bold blue] {status['total_tasks']}\n"
        f"[bold blue]Completed Tasks:[/bold blue] {status['completed_tasks']}\n"
        f"[bold blue]Failed Tasks:[/bold blue] {status['failed_tasks']}\n"
        f"[bold blue]Progress:[/bold blue] {status['progress_percentage']:.1f}%\n"
        f"[bold blue]Overall Status:[/bold blue] {status['overall_status'].upper()}",
        title="Workflow Details",
        border_style="blue"
    ))
    
    # Create a table to display tasks
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Dependencies", style="blue")
    
    # Add tasks to the table
    for task in tasks:
        # Format status
        status_str = task.status.value.upper()
        status_style = {
            TaskStatus.COMPLETED.value: "[bold green]",
            TaskStatus.FAILED.value: "[bold red]",
            TaskStatus.IN_PROGRESS.value: "[bold yellow]",
            TaskStatus.PENDING.value: "[bold blue]",
            TaskStatus.BLOCKED.value: "[bold magenta]"
        }.get(task.status.value, "")
        
        # Format dependencies
        if task.dependencies:
            dependencies = ", ".join([dep_id[:8] + "..." for dep_id in task.dependencies])
        else:
            dependencies = "None"
        
        table.add_row(
            task.id[:8] + "...",  # Show only first 8 characters of ID
            task.description[:50] + ("..." if len(task.description) > 50 else ""),
            task.task_type.replace("_", " ").title(),
            f"{status_style}{status_str}[/]",
            dependencies
        )
    
    # Display the table
    console.print(table)
    
    # Display task results
    console.print("[bold blue]Task Results:[/bold blue]")
    
    for task in tasks:
        if task.result:
            console.print(f"[bold cyan]Task ID:[/bold cyan] {task.id[:8]}...")
            console.print(f"[bold green]Success:[/bold green] {task.result.success}")
            
            if not task.result.success and task.result.error:
                console.print(f"[bold red]Error:[/bold red] {task.result.error}")
            
            if task.result.artifacts:
                console.print("[bold yellow]Artifacts:[/bold yellow]")
                
                for key, value in task.result.artifacts.items():
                    if key != "full_result":  # Skip the full result
                        if isinstance(value, str):
                            console.print(f"  [bold magenta]{key}:[/bold magenta] {value}")
                        else:
                            console.print(f"  [bold magenta]{key}:[/bold magenta] {str(value)[:100]}...")
            
            console.print()

async def resume_workflow(workflow_id: str) -> None:
    """
    Resume execution of a workflow.
    
    Args:
        workflow_id: ID of the workflow to resume
    """
    # Initialize the task executor
    assistant = EnhancedAgenticAssistant()
    task_manager = TaskManager()
    
    # Try to load the workflow
    if not task_manager.load_workflow(workflow_id):
        console.print(f"[bold red]Workflow {workflow_id} not found.[/bold red]")
        return
    
    # Get workflow status
    status = task_manager.get_workflow_status()
    
    # Check if the workflow is already completed
    if status["overall_status"] == "completed":
        console.print(f"[bold yellow]Workflow {workflow_id} is already completed.[/bold yellow]")
        return
    
    # Resume execution
    console.print(f"[bold blue]Resuming workflow {workflow_id}...[/bold blue]")
    
    # Execute the workflow
    result = await assistant.task_executor.execute_workflow(workflow_id)
    
    # Display the result
    console.print(f"[bold green]Workflow execution completed:[/bold green] {result['overall_status']}")
    console.print(f"[bold blue]Completed Tasks:[/bold blue] {result['completed_tasks']}/{result['total_tasks']}")
    
    if result["failed_tasks"] > 0:
        console.print(f"[bold red]Failed Tasks:[/bold red] {result['failed_tasks']}")

async def interactive_mode(model: Optional[str] = None) -> None:
    """
    Enter interactive mode for the Enhanced Agentic Assistant.
    
    Args:
        model: The Ollama model to use (optional)
    """
    from agentic_assistant_enhanced import enhanced_agentic_assistant_mode
    await enhanced_agentic_assistant_mode(model)

def main():
    """
    Main entry point for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Enhanced Agentic Assistant CLI")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Execute task command
    execute_parser = subparsers.add_parser("execute", help="Execute a task")
    execute_parser.add_argument("task", help="Task description")
    execute_parser.add_argument("--model", help="Ollama model to use")
    
    # List workflows command
    list_parser = subparsers.add_parser("list", help="List saved workflows")
    
    # View workflow command
    view_parser = subparsers.add_parser("view", help="View workflow details")
    view_parser.add_argument("workflow_id", help="Workflow ID")
    
    # Resume workflow command
    resume_parser = subparsers.add_parser("resume", help="Resume workflow execution")
    resume_parser.add_argument("workflow_id", help="Workflow ID")
    
    # Interactive mode command
    interactive_parser = subparsers.add_parser("interactive", help="Enter interactive mode")
    interactive_parser.add_argument("--model", help="Ollama model to use")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "execute":
        asyncio.run(execute_task(args.task, args.model))
    elif args.command == "list":
        asyncio.run(list_workflows())
    elif args.command == "view":
        asyncio.run(view_workflow(args.workflow_id))
    elif args.command == "resume":
        asyncio.run(resume_workflow(args.workflow_id))
    elif args.command == "interactive":
        asyncio.run(interactive_mode(args.model))
    else:
        # Default to interactive mode if no command is specified
        asyncio.run(interactive_mode())

if __name__ == "__main__":
    main()

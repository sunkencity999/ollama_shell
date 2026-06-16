#!/usr/bin/env python3
"""
Test script for the enhanced task management system.

This script demonstrates the capabilities of the enhanced task management system
by executing a complex task and displaying the results.
"""

import asyncio
import logging
from rich.console import Console
from rich.panel import Panel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the enhanced assistant
from agentic_assistant_enhanced import EnhancedAgenticAssistant, display_agentic_assistant_result

# Initialize console for rich output
console = Console()

async def test_complex_task():
    """
    Test the enhanced task management system with a complex task.
    """
    console.print(Panel(
        "[bold green]Enhanced Task Management Test[/bold green]\n\n"
        "This test will demonstrate the capabilities of the enhanced task management system\n"
        "by executing a complex, multi-step task.",
        title="Ollama Shell",
        border_style="blue"
    ))
    
    # Define a complex task
    task = "Research the latest gaming news, create a summary document, and find images of the top 3 games mentioned"
    
    console.print(f"[bold blue]Executing complex task:[/bold blue] {task}")
    
    # Initialize the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Execute the task
    result = await assistant.execute_task(task)
    
    # Display the result
    display_agentic_assistant_result(result)
    
    # Return the result for further analysis
    return result

async def test_task_planning():
    """
    Test the task planning capabilities of the enhanced task management system.
    """
    console.print(Panel(
        "[bold green]Task Planning Test[/bold green]\n\n"
        "This test will demonstrate the task planning capabilities of the enhanced task management system\n"
        "by breaking down a complex task into subtasks without executing them.",
        title="Ollama Shell",
        border_style="blue"
    ))
    
    # Define a complex task
    task = "Create a report on the top 5 AI research papers from 2024, including summaries and key findings"
    
    console.print(f"[bold blue]Planning task:[/bold blue] {task}")
    
    # Initialize the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Plan the task
    workflow_id = await assistant.task_planner.plan_task(task)
    
    # Display the task plan
    assistant._display_task_plan(workflow_id)
    
    # Return the workflow ID for further analysis
    return workflow_id

async def main():
    """
    Main entry point for the test script.
    """
    # Display a menu of test options
    console.print(Panel(
        "[bold green]Enhanced Task Management Tests[/bold green]\n\n"
        "1. Test Complex Task Execution\n"
        "2. Test Task Planning\n"
        "3. Run All Tests",
        title="Ollama Shell",
        border_style="blue"
    ))
    
    # Get user input
    choice = input("Enter your choice (1-3): ")
    
    if choice == "1":
        await test_complex_task()
    elif choice == "2":
        await test_task_planning()
    elif choice == "3":
        await test_complex_task()
        print("\n")
        await test_task_planning()
    else:
        console.print("[bold red]Invalid choice. Exiting.[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())

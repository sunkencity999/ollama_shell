#!/usr/bin/env python3
"""
Test script for hybrid task functionality in the Enhanced Agentic Assistant.
This script tests the ability to correctly identify and handle tasks that involve
both web browsing and file creation.
"""

import asyncio
import os
import sys
from typing import Dict, Any, List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import the enhanced assistant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agentic_assistant_enhanced import EnhancedAgenticAssistant

# Initialize console for rich output
console = Console()

# Test cases for hybrid tasks
HYBRID_TASK_TESTS = [
    # Format: (task_description, expected_is_hybrid_task)
    (
        "Search for information about climate change and create a summary file",
        True
    ),
    (
        "Visit example.com and save the content to a file named 'example_content.txt'",
        True
    ),
    (
        "Find the latest news on AI from techcrunch.com and compile it into a report",
        True
    ),
    (
        "Research the history of the internet on wikipedia.org and write a summary document",
        True
    ),
    (
        "Browse cnn.com and extract the top headlines into a file",
        True
    ),
    (
        "Look up information about Mars on space.com and create a fact sheet",
        True
    ),
    # Non-hybrid tasks (web browsing only)
    (
        "Visit example.com and read the homepage",
        False
    ),
    (
        "Search for information about climate change",
        False
    ),
    # Non-hybrid tasks (file creation only)
    (
        "Create a text file with a short story about space exploration",
        False
    ),
    (
        "Write a poem about autumn and save it as autumn_poem.txt",
        False
    )
]

async def test_is_hybrid_task():
    """Test the _is_hybrid_task method."""
    # Initialize the assistant
    assistant = EnhancedAgenticAssistant()
    
    # Table for results
    table = Table(title="Hybrid Task Detection Test Results")
    table.add_column("Task Description", style="cyan")
    table.add_column("Expected Result", style="green")
    table.add_column("Actual Result", style="yellow")
    table.add_column("Pass/Fail", style="magenta")
    
    # Track pass/fail counts
    passed = 0
    failed = 0
    
    # Test each case
    for task_description, expected_result in HYBRID_TASK_TESTS:
        # Get the actual result
        actual_result = assistant._is_hybrid_task(task_description)
        
        # Check if the test passed
        passed_test = actual_result == expected_result
        
        # Update counts
        if passed_test:
            passed += 1
        else:
            failed += 1
        
        # Add to table
        table.add_row(
            task_description[:50] + ("..." if len(task_description) > 50 else ""),
            str(expected_result),
            str(actual_result),
            "[bold green]PASS[/bold green]" if passed_test else "[bold red]FAIL[/bold red]"
        )
    
    # Display the table
    console.print(table)
    
    # Display summary
    console.print(f"\n[bold]Summary:[/bold] {passed} passed, {failed} failed")
    
    # Return overall success
    return failed == 0

async def test_hybrid_task_execution():
    """Test the execution of a hybrid task."""
    # Initialize the assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test task
    test_task = "Search for information about Python programming language on python.org and create a summary file named 'python_summary.txt'"
    
    console.print(Panel(f"[bold]Testing Hybrid Task Execution[/bold]\n\nTask: {test_task}", 
                       title="Hybrid Task Execution Test", border_style="blue"))
    
    try:
        # Execute the task
        result = await assistant._handle_hybrid_task(test_task)
        
        # Check if the task was successful
        if result.get("success", False):
            console.print("[bold green]Hybrid task execution successful![/bold green]")
            
            # Display artifacts
            if "artifacts" in result:
                console.print("[bold]Artifacts:[/bold]")
                for key, value in result["artifacts"].items():
                    console.print(f"  [cyan]{key}:[/cyan] {value}")
            
            return True
        else:
            console.print("[bold red]Hybrid task execution failed![/bold red]")
            console.print(f"Error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        console.print(f"[bold red]Error during hybrid task execution:[/bold red] {str(e)}")
        return False

async def main():
    """Run all tests."""
    console.print(Panel("[bold]Hybrid Task Functionality Tests[/bold]", 
                       title="Enhanced Agentic Assistant", border_style="green"))
    
    # Test hybrid task detection
    console.print("\n[bold]Test 1: Hybrid Task Detection[/bold]")
    detection_passed = await test_is_hybrid_task()
    
    # Test hybrid task execution
    console.print("\n[bold]Test 2: Hybrid Task Execution[/bold]")
    execution_passed = await test_hybrid_task_execution()
    
    # Overall result
    if detection_passed and execution_passed:
        console.print("\n[bold green]All tests passed![/bold green]")
    else:
        console.print("\n[bold red]Some tests failed![/bold red]")

if __name__ == "__main__":
    asyncio.run(main())

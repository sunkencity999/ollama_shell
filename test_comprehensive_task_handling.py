#!/usr/bin/env python3
"""
Comprehensive test script for task classification and handling in the Enhanced Agentic Assistant.
This script tests the ability to correctly identify and handle different types of tasks:
1. Direct file creation tasks
2. Web browsing tasks
3. Hybrid tasks (web browsing + file creation)
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

# Test cases for task classification
TASK_CLASSIFICATION_TESTS = [
    # Format: (task_description, expected_is_direct_file_creation, expected_is_web_browsing, expected_is_hybrid)
    # Direct file creation tasks
    (
        "Create a text file with a short story about space exploration",
        True, False, False
    ),
    (
        "Write a poem about autumn and save it as autumn_poem.txt",
        True, False, False
    ),
    (
        "Generate a list of 10 healthy breakfast recipes and save it",
        True, False, False
    ),
    # Web browsing tasks
    (
        "Visit example.com and read the homepage",
        False, True, False
    ),
    (
        "Search for information about climate change",
        False, True, False
    ),
    (
        "What is the latest news on CNN?",
        False, True, False
    ),
    # Hybrid tasks
    (
        "Search for information about climate change and create a summary file",
        False, False, True
    ),
    (
        "Visit example.com and save the content to a file named 'example_content.txt'",
        False, False, True
    ),
    (
        "Find the latest news on AI from techcrunch.com and compile it into a report",
        False, False, True
    )
]

async def test_task_classification():
    """Test the task classification methods."""
    # Initialize the assistant
    assistant = EnhancedAgenticAssistant()
    
    # Table for results
    table = Table(title="Task Classification Test Results")
    table.add_column("Task Description", style="cyan", width=40)
    table.add_column("Expected Classification", style="green")
    table.add_column("Actual Classification", style="yellow")
    table.add_column("Details", style="blue", width=30)
    table.add_column("Pass/Fail", style="magenta")
    
    # Track pass/fail counts
    passed = 0
    failed = 0
    
    # Test each case
    for task_description, expected_direct, expected_web, expected_hybrid in TASK_CLASSIFICATION_TESTS:
        # Get the actual results
        actual_direct = assistant._is_direct_file_creation_task(task_description)
        actual_web = assistant._is_web_browsing_task(task_description)
        actual_hybrid = assistant._is_hybrid_task(task_description)
        
        # Determine the expected and actual classification
        expected_class = "Direct File Creation" if expected_direct else ("Web Browsing" if expected_web else ("Hybrid" if expected_hybrid else "Unknown"))
        actual_class = "Direct File Creation" if actual_direct else ("Web Browsing" if actual_web else ("Hybrid" if actual_hybrid else "Unknown"))
        
        # Check if the test passed
        passed_test = (actual_direct == expected_direct and 
                       actual_web == expected_web and 
                       actual_hybrid == expected_hybrid)
        
        # Create details string
        details = f"Expected: D={expected_direct}, W={expected_web}, H={expected_hybrid}\nActual: D={actual_direct}, W={actual_web}, H={actual_hybrid}"
        
        # Update counts
        if passed_test:
            passed += 1
        else:
            failed += 1
            console.print(f"[bold red]Failed test:[/bold red] {task_description}")
            console.print(f"  Expected: Direct={expected_direct}, Web={expected_web}, Hybrid={expected_hybrid}")
            console.print(f"  Actual: Direct={actual_direct}, Web={actual_web}, Hybrid={actual_hybrid}")
        
        # Add to table
        table.add_row(
            task_description[:40] + ("..." if len(task_description) > 40 else ""),
            expected_class,
            actual_class,
            details,
            "[bold green]PASS[/bold green]" if passed_test else "[bold red]FAIL[/bold red]"
        )
    
    # Display the table
    console.print(table)
    
    # Display summary
    console.print(f"\n[bold]Summary:[/bold] {passed} passed, {failed} failed")
    
    # Return overall success
    return failed == 0

async def test_task_execution():
    """Test the execution of different types of tasks."""
    # Initialize the assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test tasks
    test_tasks = [
        # Direct file creation
        "Create a short text file named 'test_file.txt' with a greeting message",
        # Web browsing
        "Search for information about Python programming language",
        # Hybrid
        "Search for information about Python and create a summary file named 'python_info.txt'"
    ]
    
    # Table for results
    table = Table(title="Task Execution Test Results")
    table.add_column("Task Type", style="cyan")
    table.add_column("Task Description", style="green", width=40)
    table.add_column("Success", style="yellow")
    table.add_column("Artifacts", style="magenta", width=30)
    
    # Track pass/fail counts
    passed = 0
    failed = 0
    
    # Test each task
    for i, task in enumerate(test_tasks):
        task_type = ["Direct File Creation", "Web Browsing", "Hybrid"][i]
        
        console.print(f"\n[bold]Testing {task_type} Task:[/bold] {task}")
        
        try:
            # Execute the task
            result = await assistant.execute_task(task)
            
            # Check if the task was successful
            success = result.get("success", False)
            
            # Format artifacts for display
            artifacts = ""
            if "artifacts" in result:
                for key, value in result["artifacts"].items():
                    if key == "content_preview" and value:
                        value = value[:50] + "..." if len(value) > 50 else value
                    artifacts += f"{key}: {value}\n"
            
            # Update counts
            if success:
                passed += 1
            else:
                failed += 1
            
            # Add to table
            table.add_row(
                task_type,
                task[:40] + ("..." if len(task) > 40 else ""),
                "[bold green]SUCCESS[/bold green]" if success else "[bold red]FAILED[/bold red]",
                artifacts
            )
        except Exception as e:
            # Add error to table
            table.add_row(
                task_type,
                task[:40] + ("..." if len(task) > 40 else ""),
                "[bold red]ERROR[/bold red]",
                str(e)
            )
            failed += 1
    
    # Display the table
    console.print(table)
    
    # Display summary
    console.print(f"\n[bold]Summary:[/bold] {passed} passed, {failed} failed")
    
    # Return overall success
    return failed == 0

async def main():
    """Run all tests."""
    console.print(Panel("[bold]Comprehensive Task Handling Tests[/bold]", 
                       title="Enhanced Agentic Assistant", border_style="green"))
    
    # Test task classification
    console.print("\n[bold]Test 1: Task Classification[/bold]")
    classification_passed = await test_task_classification()
    
    # Test task execution
    console.print("\n[bold]Test 2: Task Execution[/bold]")
    execution_passed = await test_task_execution()
    
    # Overall result
    if classification_passed and execution_passed:
        console.print("\n[bold green]All tests passed![/bold green]")
    else:
        console.print("\n[bold red]Some tests failed![/bold red]")

if __name__ == "__main__":
    asyncio.run(main())

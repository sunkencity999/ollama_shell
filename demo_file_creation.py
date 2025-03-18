#!/usr/bin/env python3
"""
Demo script to showcase the enhanced file creation functionality.

This script demonstrates how the Enhanced Agentic Assistant handles various
file creation tasks with different phrasings and requirements.
"""

import asyncio
import logging
import os
import sys
import re
from typing import Dict, Any, Optional
from unittest import mock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the current directory to the path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary modules
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from agentic_ollama import AgenticOllama
from task_manager import TaskManager, TaskPlanner, TaskExecutor

async def demo_direct_file_creation():
    """
    Demonstrate direct file creation with the Enhanced Agentic Assistant.
    """
    print("\n=== Demonstrating Direct File Creation ===\n")
    
    # Mock the create_file method for demo purposes
    async def mock_create_file(task_description, filename=None):
        # Extract filename from task description if not provided
        if not filename:
            # Try various patterns to extract filename
            save_as_match = re.search(r'save\s+(?:it|this|the\s+\w+)\s+(?:to|as|in)\s+[\'\"]*([\w\-\.]+)[\'\"]*', task_description, re.IGNORECASE)
            if save_as_match:
                filename = save_as_match.group(1).strip()
            else:
                # Default filenames based on content type
                if "story" in task_description.lower():
                    filename = "story.txt"
                elif "poem" in task_description.lower():
                    filename = "poem.txt"
                elif "essay" in task_description.lower():
                    filename = "essay.txt"
                elif "document" in task_description.lower():
                    filename = "document.txt"
                elif "recipe" in task_description.lower():
                    filename = "recipe.txt"
                else:
                    filename = "document.txt"
        
        # Extract file type
        file_type = filename.split(".")[-1] if "." in filename else "txt"
        
        # Generate a content preview
        content_preview = f"This is a mock content for: {task_description[:100]}..."
        
        # Return a successful result
        return {
            "success": True,
            "task_type": "file_creation",
            "result": {
                "filename": filename,
                "file_type": file_type,
                "content_preview": content_preview
            },
            "message": "File created successfully"
        }
    
    # Initialize the Enhanced Agentic Assistant with mocked AgenticOllama
    assistant = EnhancedAgenticAssistant()
    assistant.agentic_ollama.create_file = mock.AsyncMock(side_effect=mock_create_file)
    
    # Test cases for direct file creation with different phrasings
    test_cases = [
        "Create a file with a short story about a space explorer who discovers a new planet",
        "Write a poem about the ocean and save it as ocean_poem.txt",
        "Create a document called project_ideas.txt with ideas for my next project",
        "Write an essay about climate change",
        "Create a recipe for chocolate chip cookies and save it as cookies.txt"
    ]
    
    for i, task in enumerate(test_cases, 1):
        print(f"Test Case {i}: {task}")
        result = await assistant.execute_task(task)
        
        print(f"Success: {result.get('success', False)}")
        
        if result.get("success", False) and "result" in result and isinstance(result["result"], dict):
            print(f"Filename: {result['result'].get('filename', 'Unknown')}")
            print(f"Content Preview: {result['result'].get('content_preview', 'No preview available')[:100]}...\n")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}\n")

async def demo_complex_workflow():
    """
    Demonstrate complex workflow with file creation tasks.
    """
    print("\n=== Demonstrating Complex Workflow with File Creation ===\n")
    
    # Mock the create_file method for demo purposes
    async def mock_create_file(task_description, filename=None):
        # Extract filename from task description if not provided
        if not filename:
            # Try various patterns to extract filename
            save_as_match = re.search(r'save\s+(?:it|this|the\s+\w+)\s+(?:to|as|in)\s+[\'\"]*([\w\-\.]+)[\'\"]*', task_description, re.IGNORECASE)
            if save_as_match:
                filename = save_as_match.group(1).strip()
            else:
                # Default filenames based on content type
                if "story" in task_description.lower():
                    filename = "story.txt"
                elif "poem" in task_description.lower():
                    filename = "poem.txt"
                elif "essay" in task_description.lower():
                    filename = "essay.txt"
                elif "document" in task_description.lower():
                    filename = "document.txt"
                elif "recipe" in task_description.lower():
                    filename = "recipe.txt"
                else:
                    filename = "document.txt"
        
        # Extract file type
        file_type = filename.split(".")[-1] if "." in filename else "txt"
        
        # Generate a content preview
        content_preview = f"This is a mock content for: {task_description[:100]}..."
        
        # Return a successful result
        return {
            "success": True,
            "task_type": "file_creation",
            "result": {
                "filename": filename,
                "file_type": file_type,
                "content_preview": content_preview
            },
            "message": "File created successfully"
        }
    
    # Mock the execute_task method for web browsing
    async def mock_execute_task(task_description):
        return {
            "success": True,
            "task_type": "web_browsing",
            "result": {
                "information": [f"Mock information about {task_description[:50]}..."],
                "headlines": [f"Mock headline about {task_description[:30]}..."],
                "url": "https://example.com/mock-url"
            },
            "message": "Web browsing completed successfully"
        }
    
    # Initialize components with mocks
    agentic_ollama = AgenticOllama()
    agentic_assistant = EnhancedAgenticAssistant()
    
    # Apply mocks
    agentic_assistant.agentic_ollama.create_file = mock.AsyncMock(side_effect=mock_create_file)
    agentic_assistant.execute_task = mock.AsyncMock(side_effect=mock_execute_task)
    
    # Create task planner and executor
    task_planner = TaskPlanner(agentic_ollama)
    task_manager = TaskManager()
    task_executor = TaskExecutor(agentic_assistant, task_manager)
    
    # Complex tasks that involve file creation
    complex_tasks = [
        "Research information about renewable energy and create a summary document",
        "Find information about healthy eating habits and write a short guide",
        "Look up the history of jazz music and write a brief overview",
        "Research the benefits of meditation and create a beginner's guide"
    ]
    
    for i, task in enumerate(complex_tasks, 1):
        print(f"\nComplex Test Case {i}: {task}")
        
        # Plan the task
        print(f"Planning task: {task}")
        workflow_id = await task_planner.plan_task(task)
        print(f"Created workflow: {workflow_id}")
        
        # Execute the workflow
        result = await task_executor.execute_workflow(workflow_id)
        
        # Load the workflow and get tasks
        task_manager.load_workflow(workflow_id)
        tasks = task_manager.get_all_tasks()
        completed_tasks = sum(1 for task in tasks if task.status == "completed")
        failed_tasks = sum(1 for task in tasks if task.status == "failed")
        
        print(f"Workflow execution completed with {completed_tasks} completed tasks and {failed_tasks} failed tasks")
        
        # Display the results of each task
        # Tasks are already loaded from the previous step
        for task in tasks:
            print(f"Task: {task.description}")
            print(f"Type: {task.task_type}")
            print(f"Status: {task.status}")
            print(f"Success: {task.result.success if task.result else False}")
            
            if task.result and task.result.artifacts:
                print("Artifacts:")
                for key, value in task.result.artifacts.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  - {key}: {value[:100]}...")
                    else:
                        print(f"  - {key}: {value}")
            print()

async def main():
    """
    Main function to run the demo.
    """
    print("Starting file creation demo...\n")
    
    # Demonstrate direct file creation
    await demo_direct_file_creation()
    
    # Demonstrate complex workflow with file creation
    await demo_complex_workflow()
    
    print("Demo completed!")

if __name__ == "__main__":
    asyncio.run(main())

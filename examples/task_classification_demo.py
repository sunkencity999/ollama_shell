#!/usr/bin/env python3
"""
Task Classification Demo

This script demonstrates the improved task classification and execution features
of the Enhanced Agentic Assistant, particularly focusing on file creation tasks.
"""

import asyncio
import os
import time
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from task_manager import TaskManager, TaskPlanner, TaskExecutor, Task, TaskStatus

async def run_demo():
    """
    Run the task classification demo.
    """
    print("\n===== Task Classification Demo =====")
    print("This demo will test various task descriptions to demonstrate the improved task classification.")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    task_manager = assistant.task_manager
    
    # Test cases for task classification
    test_cases = [
        # File creation tasks with explicit filenames
        "Write a short story about space exploration and save it to space_story.txt",
        "Create a poem about autumn and save it as autumn_poem.txt",
        "Write a recipe for chocolate cake and save it to recipes/chocolate_cake.txt",
        
        # File creation tasks with implicit filenames
        "Write a short story about dragons",
        "Create a list of the top 10 movies of all time",
        "Write a summary of the latest technology trends",
        
        # Web browsing tasks
        "Get headlines from https://cnn.com",
        "Find information about climate change on Wikipedia",
        "Search for recipes for vegetarian lasagna",
        
        # Ambiguous tasks that should be classified as file creation
        "Write a story and save it",
        "Create a document with my shopping list",
        "Write down my thoughts about the book I just read"
    ]
    
    # Create a workflow for each test case
    print("\n===== Creating Workflows =====")
    workflow_ids = []
    task_ids = []
    
    for i, test_case in enumerate(test_cases):
        workflow_id = task_manager.create_workflow(f"Test Case {i+1}")
        workflow_ids.append(workflow_id)
        
        # Add the task to the workflow
        task_id = task_manager.add_task(
            description=test_case,
            task_type="general"  # Start with general type to test classification
        )
        task_ids.append(task_id)
        
        print(f"Created workflow {i+1}: {test_case}")
    
    # Execute each workflow
    print("\n===== Executing Workflows =====")
    task_executor = TaskExecutor(assistant, task_manager)
    
    results = []
    for i, (workflow_id, task_id) in enumerate(zip(workflow_ids, task_ids)):
        print(f"\nExecuting workflow {i+1}: {test_cases[i]}")
        result = await task_executor.execute_workflow(workflow_id)
        results.append(result)
        
        # Get the workflow status
        status = task_manager.get_workflow_status()
        print(f"  Status: {status['overall_status']}")
        
        # Get the task classification
        task = task_manager.tasks[task_id]
        print(f"  Task type: {task.task_type}")
        print(f"  Task status: {task.status.value}")
        
        # If the task was completed, show the result
        if task.result:
            if task.task_type == "file_creation" and task.result.artifacts.get("filename"):
                print(f"  Created file: {task.result.artifacts['filename']}")
            elif task.task_type == "web_browsing" and task.result.artifacts.get("url"):
                print(f"  Browsed URL: {task.result.artifacts['url']}")
            
        # Reset the task manager for the next workflow
        task_manager.tasks = {}
        task_manager.task_dependencies = {}
        time.sleep(1)  # Brief pause between workflows
    
    # Print summary
    print("\n===== Classification Summary =====")
    file_creation_count = sum(1 for result in results if "file_creation" in str(result))
    web_browsing_count = sum(1 for result in results if "web_browsing" in str(result))
    general_count = len(results) - file_creation_count - web_browsing_count
    
    print(f"File creation tasks: {file_creation_count}")
    print(f"Web browsing tasks: {web_browsing_count}")
    print(f"General tasks: {general_count}")
    
    print("\n===== Demo Completed =====")

if __name__ == "__main__":
    asyncio.run(run_demo())

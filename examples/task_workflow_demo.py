#!/usr/bin/env python3
"""
Task Workflow Demo

This script demonstrates the task management features of the Enhanced Agentic Assistant.
It creates a workflow with multiple tasks and executes them in sequence.
"""

import asyncio
import os
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from task_manager import TaskManager, TaskPlanner, TaskExecutor, Task, TaskStatus

async def run_demo():
    """
    Run the task workflow demo.
    """
    print("\n===== Task Workflow Demo =====")
    print("This demo will create a workflow with multiple tasks and execute them in sequence.")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    
    # Create a workflow
    workflow_id = assistant.task_manager.create_workflow("News Analysis Workflow")
    print(f"\nCreated workflow: {workflow_id}")
    
    # Add tasks to the workflow
    tasks = [
        {
            "description": "Get headlines from https://cnn.com",
            "task_type": "web_browsing",
            "dependencies": []
        },
        {
            "description": "Analyze the sentiment of the headlines",
            "task_type": "general",
            "dependencies": [1]  # Depends on the first task
        },
        {
            "description": "Write a summary of the news and save it to news_analysis.txt",
            "task_type": "file_creation",
            "dependencies": [1, 2]  # Depends on the first and second tasks
        }
    ]
    
    # Add tasks to the workflow
    task_ids = []
    for task_data in tasks:
        # Map dependency indices to actual task IDs
        dependencies = [task_ids[dep_idx-1] for dep_idx in task_data["dependencies"] if dep_idx-1 < len(task_ids)]
        
        task_id = assistant.task_manager.add_task(
            description=task_data["description"],
            task_type=task_data["task_type"],
            dependencies=dependencies
        )
        task_ids.append(task_id)
        print(f"Added task: {task_data['description']} (ID: {task_id})")
    
    # Execute the workflow
    print("\n===== Executing Workflow =====")
    task_executor = TaskExecutor(assistant, assistant.task_manager)
    status = await task_executor.execute_workflow(workflow_id)
    
    # Get the workflow status
    status = assistant.task_manager.get_workflow_status()
    print("\n===== Workflow Status =====")
    print(f"Total Tasks: {status['total_tasks']}")
    print(f"Completed Tasks: {status['completed_tasks']}")
    print(f"Failed Tasks: {status['failed_tasks']}")
    print(f"Pending Tasks: {status['pending_tasks']}")
    print(f"In Progress Tasks: {status['in_progress_tasks']}")
    
    # Display the final results
    print("\n===== Final Results =====")
    if os.path.exists("/Users/christopher.bradford/Documents/news_analysis.txt"):
        print("News analysis file created successfully!")
        print("\nPreview of the news analysis:")
        with open("/Users/christopher.bradford/Documents/news_analysis.txt", "r") as f:
            content = f.read()
            preview = content[:300] + "..." if len(content) > 300 else content
            print(preview)
    else:
        print("News analysis file not created.")
    
    print("\n===== Demo Completed =====")

if __name__ == "__main__":
    asyncio.run(run_demo())

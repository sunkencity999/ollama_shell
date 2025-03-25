#!/usr/bin/env python3
import asyncio
import os
import logging
from agentic_assistant import AgenticAssistant
from agentic_ollama import AgenticOllama
from task_manager import TaskManager, TaskExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_simple_file_creation():
    """Test creating a file with a specific filename"""
    print("\n=== Testing Simple File Creation ===\n")
    
    # Initialize components
    agentic_ollama = AgenticOllama()
    assistant = AgenticAssistant()
    assistant.agentic_ollama = agentic_ollama
    
    # Create task manager and executor
    task_manager = TaskManager()
    task_executor = TaskExecutor(assistant, task_manager)
    
    # Create a workflow first
    workflow_description = "Create an epic poem about Harriet Tubman"
    print(f"Creating workflow: {workflow_description}")
    workflow_id = task_manager.create_workflow(workflow_description)
    
    # Create a task for generating an epic poem about Harriet Tubman
    task_description = "Create an epic poem about Harriet Tubman and save it as HarrietsOpus.doc"
    
    print(f"Creating task: {task_description}")
    task_id = task_manager.add_task(
        description=task_description,
        task_type="file_creation"
    )
    
    # Execute the workflow which contains our task
    print(f"Executing workflow {workflow_id}...")
    result = await task_executor.execute_workflow(workflow_id)
    
    # Check the workflow execution result
    print("\n=== Workflow Execution Result ===")
    print(f"Workflow ID: {workflow_id}")
    print(f"Completed Tasks: {result.get('completed_tasks', 0)}")
    print(f"Failed Tasks: {result.get('failed_tasks', 0)}")
    print(f"Pending Tasks: {result.get('pending_tasks', 0)}")
    
    # Get the task to check the result
    task = task_manager.get_task(task_id)
    
    if task and task.result and task.result.success:
        print("\n=== Task Execution Successful ===")
        print(f"Task ID: {task_id}")
        print(f"Task Description: {task_description}")
        
        # Print the artifacts
        if task.result.artifacts:
            print("\nArtifacts:")
            for key, value in task.result.artifacts.items():
                if key != "content" and key != "full_result":  # Skip content to keep output clean
                    print(f"  - {key}: {value}")
            
            # Check if the filename was correctly extracted and used
            filename = task.result.artifacts.get("filename", "")
            if filename == "HarrietsOpus.doc":
                print("\n✅ SUCCESS: Filename was correctly extracted and used!")
            else:
                print(f"\n❌ ERROR: Incorrect filename used. Expected 'HarrietsOpus.doc', got '{filename}'")
            
            # Check if the file was created
            full_path = task.result.artifacts.get("full_path", "")
            if full_path and os.path.exists(full_path):
                print(f"✅ SUCCESS: File was created at: {full_path}")
                
                # Print a preview of the content
                print("\nContent Preview:")
                with open(full_path, 'r') as f:
                    content = f.read()
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(preview)
            else:
                print(f"❌ ERROR: File was not created at the expected path: {full_path}")
    else:
        print("\n=== Task Execution Failed ===")
        error_message = task.result.error if task and task.result else "Unknown error"
        print(f"Error: {error_message}")

if __name__ == "__main__":
    asyncio.run(test_simple_file_creation())

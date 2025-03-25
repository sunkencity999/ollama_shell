#!/usr/bin/env python3
import asyncio
import os
import logging
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from agentic_ollama import AgenticOllama
from task_manager import TaskManager, TaskExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_harriet_tubman_epic_poem():
    """
    Test creating an epic poem about Harriet Tubman and saving it as HarrietsOpus.doc
    This tests the improved filename extraction and file creation logic
    """
    print("\n=== Testing Harriet Tubman Epic Poem File Creation ===\n")
    
    # Initialize components
    agentic_ollama = AgenticOllama()
    assistant = EnhancedAgenticAssistant()
    assistant.agentic_ollama = agentic_ollama
    
    # Create task manager and executor
    task_manager = TaskManager()
    task_executor = TaskExecutor(assistant, task_manager)
    
    # Create a task for generating an epic poem about Harriet Tubman
    task_description = "Create an epic poem about Harriet Tubman and save it as \"HarrietsOpus.doc\""
    
    print(f"Creating task: {task_description}")
    task_id = task_manager.create_task(
        description=task_description,
        task_type="file_creation"
    )
    
    # Execute the task
    print(f"Executing task {task_id}...")
    result = await task_executor.execute_task(task_id)
    
    # Check the result
    if result.success:
        print("\n=== Task Execution Successful ===")
        print(f"Task ID: {task_id}")
        print(f"Task Description: {task_description}")
        
        # Print the artifacts
        if result.artifacts:
            print("\nArtifacts:")
            for key, value in result.artifacts.items():
                if key != "content" and key != "full_result":  # Skip content to keep output clean
                    print(f"  - {key}: {value}")
            
            # Check if the filename was correctly extracted and used
            filename = result.artifacts.get("filename", "")
            if filename == "HarrietsOpus.doc":
                print("\n✅ SUCCESS: Filename was correctly extracted and used!")
            else:
                print(f"\n❌ ERROR: Incorrect filename used. Expected 'HarrietsOpus.doc', got '{filename}'")
            
            # Check if the file was created
            full_path = result.artifacts.get("full_path", "")
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
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(test_harriet_tubman_epic_poem())

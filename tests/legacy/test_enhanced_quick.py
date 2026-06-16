#!/usr/bin/env python3
"""
Quick test script for the file creation task handling in the Enhanced Agentic Assistant.
"""
import asyncio
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def test():
    """Test file creation task handling in the Enhanced Agentic Assistant"""
    print("\n=== Testing Enhanced Agentic Assistant Integration ===\n")
    
    # Test case
    task = 'Create a short haiku about kittens in space, and save it to my Documents folder as "kittens.txt"'
    print(f"Test Case: \"{task}\"")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    print("Successfully initialized EnhancedAgenticAssistant")
    
    # Execute the task
    try:
        result = await assistant.execute_task(task)
        print(f"Task execution successful: {result.get('success', False)}")
        
        # Check if the task was correctly identified as a complex task
        if 'subtasks' in result:
            print("Task correctly identified as a complex task")
            subtasks = result.get('subtasks', [])
            for subtask in subtasks:
                print(f"Subtask: {subtask.get('description')}")
                print(f"Task Type: {subtask.get('task_type')}")
        else:
            print("Task executed as a simple task, not a complex task with subtasks")
            print(f"Task Type: {result.get('task_type', 'unknown')}")
    except Exception as e:
        print(f"Error executing task: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test())

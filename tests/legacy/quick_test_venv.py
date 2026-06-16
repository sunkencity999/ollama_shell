#!/usr/bin/env python3
"""
Quick test script for the file creation task handling in the Agentic Assistant.
"""
import asyncio
from agentic_assistant import AgenticAssistant, display_agentic_assistant_result

async def test():
    """Test file creation task handling"""
    print("\n=== Testing File Creation Task Handling ===\n")
    
    # Test case
    task = 'Create a short haiku about kittens in space, and save it to my Documents folder as "kittens.txt"'
    print(f"Test Case: \"{task}\"")
    
    # Initialize the Agentic Assistant
    assistant = AgenticAssistant()
    print("Successfully initialized AgenticAssistant")
    
    # Execute the task
    result = await assistant.execute_task(task)
    print(f"Task execution successful: {result.get('success', False)}")
    
    # Check if the task was correctly identified as a file creation task
    if result.get('task_type') == 'file_creation':
        print("Task correctly identified as file creation")
        
        # Check if the filename was correctly extracted
        result_data = result.get('result', {})
        filename = result_data.get('filename', 'unknown')
        print(f"Filename: {filename}")
        
        # Check if the content preview is available
        content_preview = result_data.get('content_preview', '')
        if content_preview:
            print(f"Content Preview: {content_preview[:100]}...")
        else:
            print("No content preview available")
    else:
        print(f"Task identified as: {result.get('task_type', 'unknown')}")
    
    # Display the result
    display_agentic_assistant_result(result)

if __name__ == "__main__":
    # Run the test
    asyncio.run(test())

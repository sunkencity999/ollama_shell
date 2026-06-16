#!/usr/bin/env python3
"""
Test script for content generation in file creation tasks.
"""
import asyncio
import os
from agentic_assistant import AgenticAssistant
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def test_standard_assistant():
    """Test content generation with the standard Agentic Assistant"""
    print("\n=== Testing Standard Agentic Assistant Content Generation ===\n")
    
    # Test case
    task = 'Create a short haiku about kittens in space, and save it to my Documents folder as "kittens_test.txt"'
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
            print(f"Content Preview: {content_preview}")
        else:
            print("No content preview available")
            
        # Check if the file exists and has content
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                content = f.read()
                print(f"File exists and contains {len(content)} characters")
                if content.strip():
                    print("File has non-empty content")
                else:
                    print("WARNING: File is empty!")
        else:
            print(f"WARNING: File {filename} does not exist!")
    else:
        print(f"Task identified as: {result.get('task_type', 'unknown')}")

async def test_enhanced_assistant():
    """Test content generation with the Enhanced Agentic Assistant"""
    print("\n=== Testing Enhanced Agentic Assistant Content Generation ===\n")
    
    # Test case
    task = 'Create a short poem about Jim Crow America and save it to my Documents folder as "jimcrow_test.txt"'
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
                
            # Check if the file exists and has content
            filename = os.path.expanduser("~/Documents/jimcrow_test.txt")
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    content = f.read()
                    print(f"File exists and contains {len(content)} characters")
                    if content.strip():
                        print("File has non-empty content")
                        print(f"Content preview: {content[:100]}...")
                    else:
                        print("WARNING: File is empty!")
            else:
                print(f"WARNING: File {filename} does not exist!")
        else:
            print("Task executed as a simple task, not a complex task with subtasks")
            print(f"Task Type: {result.get('task_type', 'unknown')}")
    except Exception as e:
        print(f"Error executing task: {str(e)}")

async def main():
    """Run all tests"""
    await test_standard_assistant()
    print("\n" + "="*80 + "\n")
    await test_enhanced_assistant()

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())

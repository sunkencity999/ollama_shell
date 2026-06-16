#!/usr/bin/env python3
"""
Test script for the updated Agentic Assistant implementation.

This script tests the file creation task handling in the updated Agentic Assistant.
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
sys.path.insert(0, os.getcwd())

# Import the updated Agentic Assistant
from updated_agentic_assistant import AgenticAssistant, display_agentic_assistant_result

async def test_file_creation():
    """Test file creation task handling"""
    print("\n=== Testing File Creation Task Handling ===\n")
    
    # Test cases
    test_cases = [
        'Write a short story about a boy in Africa who loves ham sandwiches, and has an adventure trying to find one. Save it to my Documents folder as "Ham.txt"',
        'Create a file called "story.txt" with a short story about space exploration',
        'Write a poem about the ocean and save it as ocean_poem.txt',
        'Save the following text to a file named notes.txt: Hello world',
        'Create a document about jazz history and save it in my Documents folder',
        'Write a short story and save it as "adventure.txt"'
    ]
    
    # Initialize the Agentic Assistant
    assistant = AgenticAssistant()
    
    # Test each case
    for i, task in enumerate(test_cases):
        print(f"\nTest Case {i+1}: \"{task}\"")
        
        # Execute the task
        result = await assistant.execute_task(task)
        
        # Display the result
        print(f"Task Type: {result.get('task_type', 'unknown')}")
        print(f"Success: {result.get('success', False)}")
        print(f"Message: {result.get('message', 'No message')}")
        
        # Display the file result
        if result.get("success", False) and result.get("task_type") == "file_creation":
            file_result = result.get("result", {})
            print(f"Filename: {file_result.get('filename', 'unknown')}")
            print(f"File Type: {file_result.get('file_type', '')}")
            print(f"Content Preview: {file_result.get('content_preview', '')[:100]}...")
        
        print("-" * 50)
        
        # Display the result using the display function
        display_agentic_assistant_result(result)

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_file_creation())

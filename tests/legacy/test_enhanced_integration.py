#!/usr/bin/env python3
"""
Test script for the integration of the fixed file creation task handling with the Enhanced Agentic Assistant.

This script tests that the Enhanced Agentic Assistant correctly handles file creation tasks.
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

# Import the Enhanced Agentic Assistant
try:
    from agentic_assistant_enhanced import EnhancedAgenticAssistant
    print("Successfully imported EnhancedAgenticAssistant")
except ImportError as e:
    logger.error(f"Error importing EnhancedAgenticAssistant: {str(e)}")
    print(f"Error importing EnhancedAgenticAssistant: {str(e)}")
    sys.exit(1)

async def test_enhanced_integration():
    """Test the integration of the fixed file creation task handling with the Enhanced Agentic Assistant"""
    print("\n=== Testing Enhanced Agentic Assistant Integration ===\n")
    
    # Test cases
    test_cases = [
        'Write a short story about a robot who learns to feel emotions. Save it as "robot_emotions.txt"',
        'Create a document about the history of artificial intelligence and save it in my Documents folder'
    ]
    
    # Initialize the Enhanced Agentic Assistant
    try:
        assistant = EnhancedAgenticAssistant()
        print("Successfully initialized EnhancedAgenticAssistant")
    except Exception as e:
        logger.error(f"Error initializing EnhancedAgenticAssistant: {str(e)}")
        print(f"Error initializing EnhancedAgenticAssistant: {str(e)}")
        sys.exit(1)
    
    # Test each case
    for i, task in enumerate(test_cases):
        print(f"\nTest Case {i+1}: \"{task}\"")
        
        # Execute the task
        try:
            result = await assistant.execute_task(task)
            print(f"Task execution successful: {result.get('success', False)}")
            
            # Check if the task was correctly identified as a file creation task
            if 'subtasks' in result:
                subtasks = result.get('subtasks', [])
                for subtask in subtasks:
                    if subtask.get('task_type') == 'file_creation':
                        print("Task correctly identified as file creation")
                        
                        # Check if the filename was correctly extracted
                        subtask_result = subtask.get('result', {})
                        filename = subtask_result.get('filename', 'unknown')
                        print(f"Filename: {filename}")
                        
                        # Check if the content preview is available
                        content_preview = subtask_result.get('content_preview', '')
                        if content_preview:
                            print(f"Content Preview: {content_preview[:100]}...")
                        else:
                            print("No content preview available")
            else:
                print("Task executed as a simple task, not a complex task with subtasks")
                
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
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            print(f"Error executing task: {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_enhanced_integration())

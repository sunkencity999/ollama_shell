#!/usr/bin/env python3
"""
Test script for the enhanced agentic assistant's search functionality.
This script tests the assistant's ability to perform a hybrid task that involves
both web browsing and file creation.
"""

import asyncio
import os
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def test_hybrid_task():
    """Test the assistant's ability to perform a hybrid task."""
    print("Testing enhanced agentic assistant's search functionality...")
    
    # Initialize the assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test hybrid task
    task = "Search for information about the latest developments in renewable energy technologies and create a detailed report called renewable_energy_report.txt"
    
    print(f"Executing task: '{task}'")
    
    # Execute the task
    result = await assistant.execute_task(task)
    
    # Print the result
    print("\nTask execution result:")
    print("-" * 80)
    print(result.get('content', 'No content returned'))
    print("-" * 80)
    
    # Check if the file was created
    file_path = os.path.expanduser("~/Documents/renewable_energy_report.txt")
    if os.path.exists(file_path):
        print(f"\nFile created successfully: {file_path}")
        
        # Print file stats
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size} bytes")
        
        # Print file preview
        print("\nFile content preview:")
        print("-" * 80)
        with open(file_path, 'r') as f:
            content = f.read()
            preview_length = min(1000, len(content))
            print(content[:preview_length] + "..." if len(content) > preview_length else content)
        print("-" * 80)
    else:
        print(f"\nFile was not created: {file_path}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_task())

#!/usr/bin/env python3
"""
Task Execution Demo

This script demonstrates the improved task execution features of the Enhanced Agentic Assistant,
including detailed step-by-step feedback and structured output for task artifacts.
"""

import asyncio
import os
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def run_demo():
    """
    Run the task execution demo.
    """
    print("\n===== Task Execution Demo =====")
    print("This demo will showcase the improved task execution features with detailed feedback.")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for different task types
    test_cases = [
        # File creation task
        "Write a short story about space exploration and save it to space_adventure.txt",
        
        # Web browsing task
        "Get the top headlines from CNN",
        
        # Combined task (will be handled as a complex task)
        "Find information about climate change and write a summary to climate_report.txt"
    ]
    
    # Execute each task
    print("\n===== Executing Tasks =====")
    
    for i, test_case in enumerate(test_cases):
        print(f"\n----- Task {i+1}: {test_case} -----")
        
        # Execute the task
        result = await assistant.execute_task(test_case)
        
        # Print the task execution result
        print("\n----- Task Execution Result -----")
        print(f"Success: {result.get('success', False)}")
        print(f"Task Type: {result.get('task_type', 'unknown')}")
        print(f"Message: {result.get('message', '')}")
        
        # Display artifacts if available
        if 'result' in result and 'artifacts' in result['result']:
            artifacts = result['result']['artifacts']
            print("\nArtifacts:")
            for key, value in artifacts.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
        
        # Pause between tasks
        if i < len(test_cases) - 1:
            print("\nPress Enter to continue to the next task...")
            await asyncio.to_thread(input)
    
    print("\n===== Demo Completed =====")

if __name__ == "__main__":
    asyncio.run(run_demo())

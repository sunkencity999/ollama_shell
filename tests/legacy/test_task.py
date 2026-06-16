#!/usr/bin/env python3
"""
Test script for Enhanced Agentic Assistant
"""

import asyncio
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def test():
    assistant = EnhancedAgenticAssistant()
    
    # Test a complex task that involves both web browsing and file creation
    task = "Search for information about climate change and create a summary report"
    print(f"Executing task: {task}")
    
    result = await assistant.execute_task(task)
    
    print(f"Task result: {result}")
    
    # Test a file creation task
    task = "Write a short story about a robot who learns to feel emotions"
    print(f"\nExecuting task: {task}")
    
    result = await assistant.execute_task(task)
    
    print(f"Task result: {result}")

if __name__ == "__main__":
    asyncio.run(test())

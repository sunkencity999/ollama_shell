#!/usr/bin/env python3
"""
Test script to verify the fixes to the task management system.
This script tests:
1. Filename extraction from various task descriptions
2. Task classification for web browsing vs. file creation tasks
"""

import os
import sys
import asyncio
from agentic_assistant_enhanced import EnhancedAgenticAssistant
from logger import setup_logger

# Setup logger
logger = setup_logger("test_task_management_fixes")

async def test_filename_extraction():
    """Test the filename extraction functionality."""
    print("\n===== Testing Filename Extraction =====")
    
    # Create an instance of the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for filename extraction
    test_cases = [
        # Simple named files
        "Create a file named agenticAi",
        "Write a short story named myStory",
        "Generate a report named CNNReport",
        
        # Files with extensions
        "Create a file named report.txt",
        "Write a short story and save it as story.txt",
        "Generate a summary of CNN headlines and save it as cnn.txt",
        
        # Files with quotes
        "Create a file named 'my report'",
        "Write a short story and save it as \"my story.txt\"",
        
        # Complex cases
        "Research the latest AI developments and create a summary named ai_summary",
        "Find information about climate change and save it to a file named climate_report",
        "Analyze the headlines of CNN.com and save the results as cnn_analysis.txt"
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        filename = assistant._extract_filename(task)
        print(f"Test {i+1}: '{task}'")
        print(f"  Extracted filename: '{filename}'")
        print()

async def test_task_classification():
    """Test the task classification functionality."""
    print("\n===== Testing Task Classification =====")
    
    # Create an instance of the enhanced assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for task classification
    test_cases = [
        # Clear file creation tasks
        "Create a file named report.txt",
        "Write a short story and save it as story.txt",
        "Generate a poem about spring",
        
        # Clear web browsing tasks
        "Search for the latest news on AI",
        "Find information about climate change online",
        "Browse to cnn.com",
        "Visit https://www.example.com",
        
        # Complex tasks (web browsing + file creation)
        "Research the latest AI developments and create a summary named ai_summary",
        "Find information about climate change and save it to a file named climate_report",
        "Analyze the headlines of CNN.com and save the results as cnn_analysis.txt",
        "Search for recent space discoveries and compile them into a report",
        "Look up information about quantum computing on the web and create a summary"
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        is_file_creation = assistant._is_direct_file_creation_task(task)
        task_type = "file_creation" if is_file_creation else "web_browsing"
        print(f"Test {i+1}: '{task}'")
        print(f"  Classified as: {task_type}")
        print()

async def main():
    """Main function to run all tests."""
    print("===== Testing Task Management Fixes =====")
    
    # Test filename extraction
    await test_filename_extraction()
    
    # Test task classification
    await test_task_classification()
    
    print("\n===== All Tests Completed =====")

if __name__ == "__main__":
    asyncio.run(main())

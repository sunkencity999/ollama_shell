#!/usr/bin/env python3
"""
File Creation Task Test

This script tests the improved file creation task detection and handling
in the Enhanced Agentic Assistant.
"""

import asyncio
import os
import re
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def run_test():
    """
    Run the file creation task test.
    """
    print("\n===== File Creation Task Test =====")
    print("This test will verify the improved file creation task detection and handling.")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for file creation tasks
    test_cases = [
        "Write a short story about space exploration and save it to space_story.txt",
        "Create a poem about autumn and save it as autumn_poem.txt",
        "Write a recipe for chocolate cake and save it to recipes/chocolate_cake.txt",
        "Write a short story about dragons",
        "Create a list of the top 10 movies of all time",
        "Write a summary of the latest technology trends",
        "Write a story and save it",
        "Create a document with my shopping list",
        "Write down my thoughts about the book I just read"
    ]
    
    # Test each case
    print("\n===== Testing File Creation Tasks =====")
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest {i+1}: {test_case}")
        
        # Check if it's a web browsing task
        task_lower = test_case.lower()
        web_browsing_patterns = [
            "browse", "visit", "go to", "open website", "check website", 
            "look at website", "get information from", "search on", 
            "find on", "read from", "get data from", "scrape", 
            "grab headlines", "get headlines", "get news from", 
            "check news on", "get articles from", "get content from"
        ]
        url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', re.IGNORECASE)
        has_url = bool(url_pattern.search(test_case))
        is_web_browsing = has_url or any(pattern in task_lower for pattern in web_browsing_patterns)
        
        # Check if it's a direct file creation task
        direct_file_creation_patterns = [
            "create a poem", "write a poem", "save a poem",
            "create a story", "write a story", "save a story",
            "create a file", "write a file", "save a file",
            "create a text", "write a text", "save a text",
            "create a document", "write a document", "save a document",
            "create an essay", "write an essay", "save an essay",
            "create a report", "write a report", "save a report"
        ]
        is_direct_file_creation = any(pattern in task_lower for pattern in direct_file_creation_patterns) or assistant._is_direct_file_creation_task(test_case)
        
        # Determine task type
        if is_web_browsing:
            task_type = "web_browsing"
        elif is_direct_file_creation:
            task_type = "file_creation"
        else:
            task_type = "general"
            
        print(f"  Classified as: {task_type}")
        
        # Test filename extraction if it's a file creation task
        if task_type == "file_creation":
            filename = assistant._extract_filename(test_case)
            print(f"  Extracted filename: {filename}")
    
    print("\n===== Test Completed =====")

if __name__ == "__main__":
    asyncio.run(run_test())

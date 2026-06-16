#!/usr/bin/env python3
"""
File vs Web Classification Test

This script tests the task classification logic to ensure file creation tasks
are not incorrectly classified as web browsing tasks.
"""

import asyncio
import os
import re
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def run_test():
    """
    Run the file vs web classification test.
    """
    print("\n===== File vs Web Classification Test =====")
    print("This test will verify that file creation tasks are not incorrectly classified as web browsing tasks.")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases with potential for misclassification
    test_cases = [
        # Ambiguous tasks that should be file creation
        "Write a story about browsing the web",
        "Create a document about visiting websites",
        "Write an essay about search engines and save it",
        
        # Tasks with web-related content but file creation intent
        "Write a summary of the latest news from CNN",
        "Create a report about the top websites in 2024",
        "Write down information about climate change from various sources",
        
        # Tasks with both web browsing and file creation elements
        "Find information about climate change and write a summary",
        "Search for recipes for vegetarian lasagna and save them to a file",
        "Look up the history of computers and create a timeline document"
    ]
    
    # Execute each test case
    print("\n===== Testing Classification =====")
    
    file_creation_count = 0
    web_browsing_count = 0
    general_count = 0
    
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
        
        # Apply the improved classification logic
        # If both web browsing and file creation patterns are detected,
        # prioritize file creation for tasks that involve writing or creating
        if is_web_browsing and is_direct_file_creation:
            # Check for strong file creation indicators
            strong_file_indicators = ["write", "create", "save", "document", "file", "essay", "report", "story"]
            has_strong_file_indicators = any(indicator in task_lower for indicator in strong_file_indicators)
            
            if has_strong_file_indicators:
                task_type = "file_creation"
            else:
                task_type = "web_browsing"
        elif is_web_browsing:
            task_type = "web_browsing"
        elif is_direct_file_creation:
            task_type = "file_creation"
        else:
            task_type = "general"
        
        # Update counters
        if task_type == "file_creation":
            file_creation_count += 1
        elif task_type == "web_browsing":
            web_browsing_count += 1
        else:
            general_count += 1
        
        print(f"  Classified as: {task_type}")
        
        # Test filename extraction if it's a file creation task
        if task_type == "file_creation":
            filename = assistant._extract_filename(test_case)
            print(f"  Extracted filename: {filename}")
    
    # Print summary
    print("\n===== Classification Summary =====")
    print(f"File creation tasks: {file_creation_count}")
    print(f"Web browsing tasks: {web_browsing_count}")
    print(f"General tasks: {general_count}")
    
    print("\n===== Test Completed =====")

if __name__ == "__main__":
    asyncio.run(run_test())

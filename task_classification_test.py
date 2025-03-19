#!/usr/bin/env python3
"""
Task Classification Test

This script tests the task classification logic in the Enhanced Agentic Assistant,
focusing on distinguishing between file creation and web browsing tasks.
"""

import asyncio
import os
import re
from agentic_assistant_enhanced import EnhancedAgenticAssistant

async def run_test():
    """
    Run the task classification test.
    """
    print("\n===== Task Classification Test =====")
    print("This test will verify the task classification logic for file creation and web browsing tasks.")
    
    # Initialize the Enhanced Agentic Assistant
    assistant = EnhancedAgenticAssistant()
    
    # Test cases for task classification
    test_cases = [
        # File creation tasks with explicit filenames
        "Write a short story about space exploration and save it to space_story.txt",
        "Create a poem about autumn and save it as autumn_poem.txt",
        "Write a recipe for chocolate cake and save it to recipes/chocolate_cake.txt",
        
        # File creation tasks with implicit filenames
        "Write a short story about dragons",
        "Create a list of the top 10 movies of all time",
        "Write a summary of the latest technology trends",
        
        # Web browsing tasks
        "Get headlines from https://cnn.com",
        "Find information about climate change on Wikipedia",
        "Search for recipes for vegetarian lasagna",
        "Browse the web for information about artificial intelligence",
        "Visit the New York Times website",
        
        # Ambiguous tasks that should be classified as file creation
        "Write a story and save it",
        "Create a document with my shopping list",
        "Write down my thoughts about the book I just read"
    ]
    
    # Test each case
    print("\n===== Testing Task Classification =====")
    
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
        
        # Determine task type
        if is_web_browsing:
            task_type = "web_browsing"
            web_browsing_count += 1
        elif is_direct_file_creation:
            task_type = "file_creation"
            file_creation_count += 1
        else:
            task_type = "general"
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

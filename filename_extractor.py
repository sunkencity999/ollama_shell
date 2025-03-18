#!/usr/bin/env python3
"""
Filename Extractor for Ollama Shell

This module provides utilities for extracting filenames from task descriptions
and properly handling file creation tasks.
"""
import re
import os
import logging
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_filename(task_description: str) -> Optional[str]:
    """
    Extract a filename from a task description using multiple regex patterns.
    
    Args:
        task_description: The task description to extract a filename from
        
    Returns:
        The extracted filename or None if no filename was found
    """
    # Pattern 1: Match quoted filenames
    pattern1 = r'[\"\']([^\"\']+\.[a-zA-Z0-9]+)[\"\']'
    match1 = re.search(pattern1, task_description)
    
    # Pattern 2: Match "save as" or "save to" followed by a filename
    pattern2 = r'save\s+(?:it\s+)?(?:as|to)\s+[\"\']?([^\"\']+\.[a-zA-Z0-9]+)[\"\']?'
    match2 = re.search(pattern2, task_description, re.IGNORECASE)
    
    # Pattern 3: Match "called" or "named" followed by a filename
    pattern3 = r'(?:called|named)\s+[\"\']?([^\"\']+\.[a-zA-Z0-9]+)[\"\']?'
    match3 = re.search(pattern3, task_description, re.IGNORECASE)
    
    # Use the first match found
    if match1:
        return match1.group(1)
    elif match2:
        return match2.group(1)
    elif match3:
        return match3.group(1)
    
    return None

def modify_task_for_filename(task_description: str) -> Tuple[str, Optional[str]]:
    """
    Modify a task description to ensure the filename is properly used.
    
    Args:
        task_description: The original task description
        
    Returns:
        A tuple containing the modified task description and the extracted filename
    """
    # Extract the filename
    filename = extract_filename(task_description)
    
    # If a filename was found, modify the task to ensure it's used
    if filename:
        # Check if the task already has a "save as" or "save to" instruction
        if "save as" not in task_description.lower() and "save to" not in task_description.lower():
            # Add a "save as" instruction to the task
            task_description = f"{task_description} (Save as '{filename}')"
    
    return task_description, filename

def format_file_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a file creation result for display.
    
    Args:
        result: The raw file creation result
        
    Returns:
        A formatted result dictionary
    """
    # Get the filename from the result
    filename = result.get('filename', 'unknown')
    
    # Format the result
    return {
        "success": True,
        "task_type": "file_creation",
        "result": {
            "filename": filename,
            "file_type": os.path.splitext(filename)[1] if filename != 'unknown' else '',
            "content_preview": result.get('content_preview', ''),
            "full_result": result
        },
        "message": f"Successfully created file: {filename}"
    }

# Test the module if run directly
if __name__ == "__main__":
    # Test cases
    test_cases = [
        'Write a short story about a boy in Africa who loves ham sandwiches, and has an adventure trying to find one. Save it to my Documents folder as "Ham.txt"',
        'Create a file called "story.txt" with a short story about space exploration',
        'Write a poem about the ocean and save it as ocean_poem.txt',
        'Save the following text to a file named notes.txt: Hello world',
        'Create a document about jazz history and save it in my Documents folder',
        'Write a short story and save it as "adventure.txt"'
    ]
    
    # Test each case
    for i, task in enumerate(test_cases):
        print(f"Test Case {i+1}: \"{task}\"")
        modified_task, filename = modify_task_for_filename(task)
        print(f"Extracted filename: {filename}")
        print(f"Modified task: {modified_task}")
        print("-" * 50)

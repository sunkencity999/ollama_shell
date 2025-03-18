#!/usr/bin/env python3
"""
Fixed File Handler for Ollama Shell (Version 2)

This module provides a fixed implementation of the file creation task handling
for the Agentic Assistant with improved filename extraction.
"""
import os
import re
import logging
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_filename(task_description: str) -> Optional[str]:
    """
    Extract a filename from a task description.
    
    Args:
        task_description: The task description to extract a filename from
        
    Returns:
        The extracted filename or None if no filename was found
    """
    # Pattern 1: Match quoted filenames
    pattern1 = r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']'
    match1 = re.search(pattern1, task_description)
    
    # Pattern 2: Match "save as" or "save to" followed by a filename
    pattern2 = r'save\s+(?:it\s+)?(?:as|to)\s+["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'
    match2 = re.search(pattern2, task_description, re.IGNORECASE)
    
    # Pattern 3: Match "called" or "named" followed by a filename
    pattern3 = r'(?:called|named)\s+["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'
    match3 = re.search(pattern3, task_description, re.IGNORECASE)
    
    # Use the first match found
    if match1:
        return match1.group(1)
    elif match2:
        return match2.group(1)
    elif match3:
        return match3.group(1)
    
    # Fallback: Generate a filename based on the task description
    # This is used when no filename is specified in the task
    task_words = task_description.lower().split()
    
    # Try to extract a topic from the task description
    topic = None
    about_idx = task_description.lower().find('about')
    if about_idx != -1:
        # Extract the first noun after "about"
        words_after_about = task_description[about_idx + 6:].strip().split()
        if words_after_about:
            topic = words_after_about[0].strip('.,;:!?')
    
    # If we found a topic, use it as the filename
    if topic:
        return f"{topic}.txt"
    
    # Check if this is a document, story, poem, etc.
    content_type = None
    for word in ['document', 'story', 'poem', 'essay', 'report', 'note']:
        if word in task_words:
            content_type = word
            break
    
    # If we found a content type, use it as the filename
    if content_type:
        return f"{content_type}.txt"
    
    # Last resort: use a generic filename
    return "document.txt"

async def handle_file_creation(agentic_ollama, task_description: str) -> Dict[str, Any]:
    """
    Handle file creation tasks.
    
    Args:
        agentic_ollama: Instance of AgenticOllama
        task_description: Natural language description of the file to create
        
    Returns:
        Dict containing the file creation results
    """
    try:
        # Extract filename from task description if specified
        filename = extract_filename(task_description)
        
        # If a filename was found, modify the task to ensure it's used
        if filename:
            # Check if the task already has a "save as" or "save to" instruction
            if "save as" not in task_description.lower() and "save to" not in task_description.lower():
                # Add a "save as" instruction to the task
                task_description = f"{task_description} (Save as '{filename}')"
                
        # Use the create_file method from AgenticOllama
        result = await agentic_ollama.create_file(task_description)
        
        # Get the filename from the result
        filename = result.get('filename', 'unknown')
        
        # Format the result properly for task manager
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
    except Exception as e:
        logger.error(f"Error creating file: {str(e)}")
        return {
            "success": False,
            "task_type": "file_creation",
            "error": str(e),
            "message": f"Failed to create file: {str(e)}"
        }

def display_file_result(result: Dict[str, Any]) -> None:
    """
    Display a file creation result.
    
    Args:
        result: The file creation result to display
    """
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    file_result = result.get("result", {})
    
    # Check if we have a full_result field with more details
    full_result = file_result.get('full_result', {})
    
    # Get filename from the most reliable source
    filename = file_result.get('filename', 'unknown')
    if filename == 'unknown' and full_result:
        filename = full_result.get('filename', 'unknown')
    
    # Get content preview from the most reliable source
    content_preview = file_result.get('content_preview', '')
    if not content_preview and full_result:
        content_preview = full_result.get('content_preview', '')
    
    # Display the results
    console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
    console.print(f"[bold]File:[/bold] {filename}")
    console.print(f"[bold]Type:[/bold] {file_result.get('file_type', '')}")
    if content_preview:
        console.print("[bold]Content Preview:[/bold]")
        console.print(Panel(content_preview, border_style="blue"))

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
        filename = extract_filename(task)
        print(f"Extracted filename: {filename}")
        print("-" * 50)

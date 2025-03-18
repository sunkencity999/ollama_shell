"""
Final implementation of the improved file creation functionality in the Enhanced Agentic Assistant.
This file contains the corrected code for the _extract_filename, _is_direct_file_creation_task,
and _handle_file_creation methods that should be integrated into the agentic_assistant_enhanced.py file.
"""

def _extract_filename(self, task_description: str) -> str:
    """
    Extract the filename from a task description using multiple regex patterns.
    If no filename is found, generate a default one based on content type.
    
    Args:
        task_description: Description of the task
        
    Returns:
        Extracted or generated filename
    """
    logger.info(f"Extracting filename from: {task_description}")
    
    # Pattern 1: "save it to my [folder] as [filename]" - handles paths with quotes
    save_path_match = re.search(r'save\s+(?:it|this|the\s+\w+)?\s+(?:to|in)\s+(?:my\s+)?(?:[\w\s]+\s+)?folder\s+as\s+["\']+([\w\-\.\s]+\.\w+)["\']+', task_description, re.IGNORECASE)
    if save_path_match:
        filename = save_path_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 1 (path with quotes): {filename}")
        return filename
    
    # Pattern 2: "save it to/as/in [filename]" - standard pattern
    save_as_match = re.search(r'save\s+(?:it|this|the\s+\w+)\s+(?:to|as|in)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
    if save_as_match:
        filename = save_as_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 2 (standard save as): {filename}")
        return filename
    
    # Pattern 3: "save to/as/in [filename]" - shorter variant
    save_to_match = re.search(r'save\s+(?:to|as|in)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
    if save_to_match:
        filename = save_to_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 3 (short save to): {filename}")
        return filename
    
    # Pattern 4: "create/write a [content] and save it as [filename]" - compound action
    create_save_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:and|&)\s+save\s+(?:it|this)\s+(?:to|as|in)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
    if create_save_match:
        filename = create_save_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 4 (compound action): {filename}")
        return filename
    
    # Pattern 5: "create/write a [content] called/named [filename]" - named content
    called_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:called|named)\s+["\']+([\w\-\.\s]+\.\w+)["\']+', task_description, re.IGNORECASE)
    if called_match:
        filename = called_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 5 (named content): {filename}")
        return filename
    
    # Pattern 6: "create/write [filename]" - direct file creation
    create_file_match = re.search(r'(?:create|write)\s+["\']*([\w\-\.\s]+\.\w+)["\']*', task_description, re.IGNORECASE)
    if create_file_match:
        filename = create_file_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 6 (direct file): {filename}")
        return filename
    
    # Pattern 7: Look for any quoted text ending with a file extension
    quoted_filename_match = re.search(r'["\']+([\w\-\.\s]+\.\w+)["\']+', task_description, re.IGNORECASE)
    if quoted_filename_match:
        filename = quoted_filename_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 7 (quoted text): {filename}")
        return filename
    
    # If no filename is found, generate a default one based on content type
    content_type = self._detect_content_type(task_description)
    default_filename = f"{content_type}.txt"
    logger.info(f"No filename found, using default: {default_filename}")
    return default_filename

def _is_direct_file_creation_task(self, task_description: str) -> bool:
    """
    Determine if a task is a direct file creation task that should be handled directly.
    
    Args:
        task_description: Description of the task
        
    Returns:
        True if the task is a direct file creation task, False otherwise
    """
    # Pattern 1: Create a file/document with...
    pattern1 = r"create\s+(?:a|an)\s+(?:file|document|text|story|poem|essay|article|report|note)\s+(?:with|about|for|containing)"
    if re.search(pattern1, task_description, re.IGNORECASE):
        logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
        return True
    
    # Pattern 2: Write a story/poem/essay...
    pattern2 = r"write\s+(?:a|an)\s+(?:story|poem|essay|article|report|note|text|document)"
    if re.search(pattern2, task_description, re.IGNORECASE):
        logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
        return True
    
    # Pattern 3: Save as filename...
    pattern3 = r"save\s+(?:it|this|the\s+file|the\s+document)\s+as\s+([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)"
    if re.search(pattern3, task_description, re.IGNORECASE):
        logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
        return True
    
    # Pattern 4: Create a file named/called...
    pattern4 = r"create\s+(?:a|an)\s+(?:file|document)\s+(?:named|called)"
    if re.search(pattern4, task_description, re.IGNORECASE):
        logger.info(f"Detected direct file creation task: '{task_description}'. Handling directly.")
        return True
    
    # Pattern 5: Save to folder as filename...
    pattern5 = r"save\s+(?:it|this)?\s+to\s+(?:my\s+)?(?:[\w\s]+\s+)?folder\s+as\s+"
    if re.search(pattern5, task_description, re.IGNORECASE):
        logger.info(f"Detected direct file creation task with folder path: '{task_description}'. Handling directly.")
        return True
    
    # Pattern 6: Look for quoted filenames
    pattern6 = r'["\']+[\w\-\.\s]+\.\w+["\']+' 
    if re.search(pattern6, task_description, re.IGNORECASE) and ("create" in task_description.lower() or "write" in task_description.lower() or "save" in task_description.lower()):
        logger.info(f"Detected direct file creation task with quoted filename: '{task_description}'. Handling directly.")
        return True
    
    # Fallback pattern: If it contains create/write and doesn't look like a web search
    web_patterns = [r"search", r"find", r"look\s+up", r"browse", r"internet", r"web"]
    has_web_term = any(re.search(p, task_description, re.IGNORECASE) for p in web_patterns)
    
    if not has_web_term and ("create" in task_description.lower() or "write" in task_description.lower() or "save" in task_description.lower()):
        logger.info(f"Detected simple file creation task: '{task_description}'. Using standard execution.")
        return True
    
    return False

async def _handle_file_creation(self, task_description: str) -> Dict[str, Any]:
    """
    Handle file creation tasks directly, bypassing the task management system.
    This method overrides the parent class method to add enhanced functionality.
    
    Args:
        task_description: Description of the file creation task
        
    Returns:
        Dict containing the result of the file creation operation
    """
    logger.info(f"Handling file creation task directly: {task_description}")
    
    try:
        # Extract the filename from the task description using our improved method
        filename = self._extract_filename(task_description)
        
        if not filename:
            logger.error(f"No filename could be extracted from: {task_description}")
            return {
                "success": False,
                "task_type": "file_creation",
                "error": "No filename specified",
                "message": "No filename specified. Please provide a filename to save the content to."
            }
        
        # Use the AgenticOllama's create_file method directly
        result = await self.agentic_ollama.create_file(task_description, filename)
        
        # Return a properly formatted result
        success = result.get("success", False)
        message = result.get("message", "File creation completed")
        
        # Extract the result data
        result_data = {}
        if success and "result" in result and isinstance(result["result"], dict):
            result_data = {
                "filename": result["result"].get("filename", "Unknown"),
                "file_type": result["result"].get("file_type", "txt"),
                "content_preview": result["result"].get("content_preview", "No preview available")
            }
        
        return {
            "success": success,
            "task_type": "file_creation",
            "result": result_data,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error handling file creation task: {str(e)}")
        return {
            "success": False,
            "task_type": "file_creation",
            "error": str(e),
            "message": f"Failed to create file: {str(e)}"
        }

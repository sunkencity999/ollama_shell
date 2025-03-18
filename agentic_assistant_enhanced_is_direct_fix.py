"""
Updated implementation of the _is_direct_file_creation_task method to handle more patterns.
This file contains the corrected code that should be integrated into the agentic_assistant_enhanced.py file.
"""

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
    pattern6 = r'["\']+[\w\-\.]+\.\w+["\']+' 
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

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def extract_filename_improved(task_description: str) -> str:
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
    save_path_match = re.search(r'save\s+(?:it|this|the\s+\w+)?\s+(?:to|in)\s+(?:my\s+)?(?:[\w\s]+\s+)?folder\s+as\s+["\']+([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if save_path_match:
        filename = save_path_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 1 (path with quotes): {filename}")
        return filename
    
    # Pattern 2: "save it to/as/in [filename]" - standard pattern
    save_as_match = re.search(r'save\s+(?:it|this|the\s+\w+)\s+(?:to|as|in)\s+["\']*([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if save_as_match:
        filename = save_as_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 2 (standard save as): {filename}")
        return filename
    
    # Pattern 3: "save to/as/in [filename]" - shorter variant
    save_to_match = re.search(r'save\s+(?:to|as|in)\s+["\']*([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if save_to_match:
        filename = save_to_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 3 (short save to): {filename}")
        return filename
    
    # Pattern 4: "create/write a [content] and save it as [filename]" - compound action
    create_save_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:and|&)\s+save\s+(?:it|this)\s+(?:to|as|in)\s+["\']*([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if create_save_match:
        filename = create_save_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 4 (compound action): {filename}")
        return filename
    
    # Pattern 5: "create/write a [content] called/named [filename]" - named content
    called_match = re.search(r'(?:create|write)\s+a\s+[\w\s]+\s+(?:called|named)\s+["\']*([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if called_match:
        filename = called_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 5 (named content): {filename}")
        return filename
    
    # Pattern 6: "create/write [filename]" - direct file creation
    create_file_match = re.search(r'(?:create|write)\s+["\']*([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if create_file_match:
        filename = create_file_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 6 (direct file): {filename}")
        return filename
    
    # Pattern 7: Look for any quoted text ending with a file extension
    quoted_filename_match = re.search(r'["\']+([\w\-\.]+\.\w+)["\']', task_description, re.IGNORECASE)
    if quoted_filename_match:
        filename = quoted_filename_match.group(1).strip()
        logger.info(f"Extracted filename using pattern 7 (quoted text): {filename}")
        return filename
    
    # If no filename is found, return None or a default
    logger.info(f"No filename found in: {task_description}")
    return None

# Test the function with the problematic input
test_input = 'Create a poem about jim crow america and save it to my Documents folder as "jimCrow.txt"'
result = extract_filename_improved(test_input)
print(f"Extracted filename: {result}")

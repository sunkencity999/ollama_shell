#!/usr/bin/env python3
"""
Patch script for fixing file creation task handling in Agentic Assistant.

This script applies patches to the agentic_assistant.py file to fix issues with
file creation task handling, particularly with filename extraction and result display.
"""
import os
import sys
import re
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup at {backup_path}")
    return backup_path

def patch_file_creation_handler(file_path):
    """Patch the _handle_file_creation method in agentic_assistant.py"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Define the pattern to match the _handle_file_creation method
    pattern = r'async def _handle_file_creation\(self, task_description: str\) -> Dict\[str, Any\]:(.*?)(?=async def|def|class|$)'
    
    # Define the replacement
    replacement = '''async def _handle_file_creation(self, task_description: str) -> Dict[str, Any]:
        """
        Handle file creation tasks.
        
        Args:
            task_description: Natural language description of the file to create
            
        Returns:
            Dict containing the file creation results
        """
        try:
            # Extract filename from task description if specified
            import re
            
            # Pattern 1: Match quoted filenames
            pattern1 = r'[\\"\\'](.*?\\.[a-zA-Z0-9]+)[\\"\\'"]'
            match1 = re.search(pattern1, task_description)
            
            # Pattern 2: Match "save as" or "save to" followed by a filename
            pattern2 = r'save\\s+(?:it\\s+)?(?:as|to)\\s+[\\"\\'"]?(.*?\\.[a-zA-Z0-9]+)[\\"\\'"]?'
            match2 = re.search(pattern2, task_description, re.IGNORECASE)
            
            # Pattern 3: Match "called" or "named" followed by a filename
            pattern3 = r'(?:called|named)\\s+[\\"\\'"]?(.*?\\.[a-zA-Z0-9]+)[\\"\\'"]?'
            match3 = re.search(pattern3, task_description, re.IGNORECASE)
            
            # Use the first match found
            custom_filename = None
            if match1:
                custom_filename = match1.group(1)
            elif match2:
                custom_filename = match2.group(1)
            elif match3:
                custom_filename = match3.group(1)
            
            # If a filename was found, modify the task to ensure it's used
            if custom_filename:
                # Check if the task already has a "save as" or "save to" instruction
                if "save as" not in task_description.lower() and "save to" not in task_description.lower():
                    # Add a "save as" instruction to the task
                    task_description = f"{task_description} (Save as '{custom_filename}')"
                    
            # Use the create_file method from AgenticOllama
            result = await self.agentic_ollama.create_file(task_description)
            
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
            }'''
    
    # Apply the replacement using re.sub with the DOTALL flag to match across lines
    patched_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the patched content back to the file
    with open(file_path, 'w') as f:
        f.write(patched_content)
    
    logger.info("Patched _handle_file_creation method")

def patch_display_result(file_path):
    """Patch the display_agentic_assistant_result function in agentic_assistant.py"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Define the pattern to match the display_agentic_assistant_result function
    pattern = r'def display_agentic_assistant_result\(result: Dict\[str, Any\]\):(.*?)(?=def|class|$)'
    
    # Define the replacement
    replacement = '''def display_agentic_assistant_result(result: Dict[str, Any]):
    """
    Display the results of a task execution.
    
    Args:
        result: The task execution result dictionary
    """
    if result.get("success", False):
        # Format the result based on the task type
        if result.get("task_type") == "file_creation":
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
                console.print(Panel(content_preview, border_style="blue"))'''
    
    # Apply the replacement using re.sub with the DOTALL flag to match across lines
    patched_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the patched content back to the file
    with open(file_path, 'w') as f:
        f.write(patched_content)
    
    logger.info("Patched display_agentic_assistant_result function")

def main():
    """Main function to apply all patches"""
    # Define the path to the agentic_assistant.py file
    assistant_path = os.path.join(os.getcwd(), "agentic_assistant.py")
    
    # Check if the file exists
    if not os.path.exists(assistant_path):
        logger.error(f"File not found: {assistant_path}")
        sys.exit(1)
    
    # Create a backup of the file
    backup_path = backup_file(assistant_path)
    
    try:
        # Apply the patches
        patch_file_creation_handler(assistant_path)
        patch_display_result(assistant_path)
        
        logger.info("Successfully applied all patches")
        print(f"Successfully patched agentic_assistant.py")
        print(f"A backup was created at {backup_path}")
    except Exception as e:
        logger.error(f"Error applying patches: {str(e)}")
        print(f"Error: {str(e)}")
        print(f"Restoring from backup...")
        
        # Restore from backup
        shutil.copy2(backup_path, assistant_path)
        
        logger.info("Restored from backup")
        print(f"Restored from backup at {backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()

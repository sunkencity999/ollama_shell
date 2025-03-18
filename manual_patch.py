#!/usr/bin/env python3
"""
Manual Patch Script for Agentic Assistant

This script manually patches the agentic_assistant.py file to fix the file creation task handling.
"""
import os
import sys
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

def main():
    """Main function to apply the manual patch"""
    # Define the path to the agentic_assistant.py file
    assistant_path = os.path.join(os.getcwd(), "agentic_assistant.py")
    
    # Check if the file exists
    if not os.path.exists(assistant_path):
        logger.error(f"File not found: {assistant_path}")
        sys.exit(1)
    
    # Create a backup of the file
    backup_path = backup_file(assistant_path)
    
    try:
        # Read the fixed file handler code
        fixed_handler_path = os.path.join(os.getcwd(), "fixed_file_handler.py")
        with open(fixed_handler_path, 'r') as f:
            fixed_handler_code = f.read()
        
        # Read the agentic_assistant.py file
        with open(assistant_path, 'r') as f:
            assistant_code = f.read()
        
        # Add the extract_filename function to the imports section
        import_section = """
# Import the fixed file handler functions
from fixed_file_handler import extract_filename, display_file_result
"""
        
        # Find the import section and add our imports
        import_end = assistant_code.find("# Configure logging")
        if import_end == -1:
            import_end = assistant_code.find("logging.basicConfig")
        
        if import_end != -1:
            patched_code = assistant_code[:import_end] + import_section + assistant_code[import_end:]
            
            # Write the patched code back to the file
            with open(assistant_path, 'w') as f:
                f.write(patched_code)
            
            logger.info("Successfully added imports to agentic_assistant.py")
            print("Successfully patched agentic_assistant.py with fixed file handler imports")
            print(f"A backup was created at {backup_path}")
            print("\nTo complete the patch, you need to manually:")
            print("1. Replace the _handle_file_creation method in agentic_assistant.py with the one from fixed_file_handler.py")
            print("2. Update the display_agentic_assistant_result function to use display_file_result for file creation tasks")
            print("\nSee fixed_file_handler.py for the correct implementations.")
        else:
            logger.error("Could not find import section in agentic_assistant.py")
            print("Error: Could not find import section in agentic_assistant.py")
            print("Please manually add the imports from fixed_file_handler.py")
    except Exception as e:
        logger.error(f"Error applying patch: {str(e)}")
        print(f"Error: {str(e)}")
        print(f"Restoring from backup...")
        
        # Restore from backup
        shutil.copy2(backup_path, assistant_path)
        
        logger.info("Restored from backup")
        print(f"Restored from backup at {backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()

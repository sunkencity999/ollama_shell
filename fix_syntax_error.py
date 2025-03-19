#!/usr/bin/env python3
"""
Script to fix syntax errors in the Enhanced Agentic Assistant.
"""

import os
import sys

def fix_syntax_errors(file_path):
    """Fix syntax errors in the file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the syntax error in pattern6
    error_pattern = r'(?:["\']+[\w\-\.\s]+\.[\w]+["\']+|\b[\w\-\.]+\.[a-zA-Z0-9]{2,4}\b)'
    fixed_pattern = r'(?:["\']+[\\w\\-\\.\\s]+\\.[\\w]+["\']+|\\b[\\w\\-\\.]+\\.[a-zA-Z0-9]{2,4}\\b)'
    
    # Replace the problematic pattern
    updated_content = content.replace(error_pattern, fixed_pattern)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("Successfully fixed syntax errors.")
    return True

def main():
    """Main function to fix syntax errors."""
    file_path = '/Users/christopher.bradford/ollamaShell/agentic_assistant_enhanced.py'
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return 1
    
    # Make a backup of the original file
    backup_path = f"{file_path}.syntax.bak"
    with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    print(f"Created backup at {backup_path}")
    
    # Fix syntax errors
    success = fix_syntax_errors(file_path)
    
    if success:
        print("Successfully fixed syntax errors in the Enhanced Agentic Assistant.")
        return 0
    else:
        print("Failed to fix syntax errors.")
        print("Restoring from backup...")
        with open(backup_path, 'r') as src, open(file_path, 'w') as dst:
            dst.write(src.read())
        print("Restored from backup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

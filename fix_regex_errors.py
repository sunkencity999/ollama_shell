#!/usr/bin/env python3
"""
Script to fix regex syntax errors in the Enhanced Agentic Assistant.
"""

import os
import sys
import re

def fix_regex_errors(file_path):
    """Fix regex syntax errors in the file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the problematic regex patterns by adding raw string prefix and escaping properly
    # Find all regex patterns with invalid escape sequences
    pattern = r"(pattern\d+\s*=\s*r')([^']*)('"
    
    def fix_escapes(match):
        prefix = match.group(1)
        regex = match.group(2)
        suffix = match.group(3)
        
        # Fix the escape sequences
        fixed_regex = regex.replace("\\w", "\\\\w")
        fixed_regex = fixed_regex.replace("\\s", "\\\\s")
        fixed_regex = fixed_regex.replace("\\d", "\\\\d")
        fixed_regex = fixed_regex.replace("\\b", "\\\\b")
        fixed_regex = fixed_regex.replace("\\.", "\\\\.")
        fixed_regex = fixed_regex.replace("\\-", "\\\\-")
        fixed_regex = fixed_regex.replace("\\+", "\\\\+")
        
        return prefix + fixed_regex + suffix
    
    # Apply the fix
    updated_content = re.sub(pattern, fix_escapes, content)
    
    # Fix the specific problematic pattern6
    problematic = r"pattern6 = r'(?:[\"'\"]\[\w\-\.\s\]+\.\[\w\]+\[\"'\"\]\|\\\b\[\w\-\.\]+\.\[a-zA-Z0-9\]\{2,4\}\\\b)'"
    fixed = r"pattern6 = r'(?:[\"\''][\\w\\-\\.\\s]+\\.[\\w]+[\"\'']|\\b[\\w\\-\\.]+\\.[a-zA-Z0-9]{2,4}\\b)'"
    
    updated_content = updated_content.replace(problematic, fixed)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("Successfully fixed regex syntax errors.")
    return True

def main():
    """Main function to fix regex syntax errors."""
    file_path = '/Users/christopher.bradford/ollamaShell/agentic_assistant_enhanced.py'
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return 1
    
    # Make a backup of the original file
    backup_path = f"{file_path}.regex.bak"
    with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    print(f"Created backup at {backup_path}")
    
    # Fix regex syntax errors
    success = fix_regex_errors(file_path)
    
    if success:
        print("Successfully fixed regex syntax errors in the Enhanced Agentic Assistant.")
        return 0
    else:
        print("Failed to fix regex syntax errors.")
        print("Restoring from backup...")
        with open(backup_path, 'r') as src, open(file_path, 'w') as dst:
            dst.write(src.read())
        print("Restored from backup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

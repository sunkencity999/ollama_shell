#!/usr/bin/env python3
"""
Script to fix the syntax error in pattern6 with a more reliable approach.
"""

import os

def main():
    """Fix the syntax error in pattern6."""
    file_path = '/Users/christopher.bradford/ollamaShell/agentic_assistant_enhanced.py'
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find and replace the problematic pattern6 line
    old_pattern = 'pattern6 = r\'(?:["\']+\\w+\\.\\w+["\']+|\\b\\w+\\.\\w{2,4}\\b)\''
    new_pattern = 'pattern6 = r"(?:[\'\\\"]+\\w+\\.\\w+[\'\\\"]+|\\b\\w+\\.\\w{2,4}\\b)"'
    
    # Replace the pattern
    updated_content = content.replace(old_pattern, new_pattern)
    
    # Write the fixed content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("Successfully fixed the syntax error in pattern6.")

if __name__ == "__main__":
    main()

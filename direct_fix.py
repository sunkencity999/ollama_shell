#!/usr/bin/env python3
"""
Script to directly fix the syntax error in pattern6.
"""

import os

def main():
    """Fix the syntax error in pattern6."""
    file_path = '/Users/christopher.bradford/ollamaShell/agentic_assistant_enhanced.py'
    
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the line with pattern6
    for i, line in enumerate(lines):
        if "pattern6 = " in line:
            # Replace the problematic line with a fixed version
            lines[i] = '        pattern6 = r\'(?:["\']+\\w+\\.\\w+["\']+|\\b\\w+\\.\\w{2,4}\\b)\'\n'
            break
    
    # Write the fixed content back to the file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print("Successfully fixed the syntax error in pattern6.")

if __name__ == "__main__":
    main()

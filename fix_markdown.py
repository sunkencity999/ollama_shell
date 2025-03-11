#!/usr/bin/env python3
"""
Script to fix markdown linting issues in README.md by adding language specifications to code blocks.
"""

import re
import sys

def fix_code_blocks(file_path):
    """
    Add language specifications to code blocks in markdown file.
    """
    with open(file_path, 'r') as file:
        content = file.read()

    # Pattern to find code blocks without language specification
    pattern = r'```\s*\n'
    
    # Replace with appropriate language based on content
    def replacement(match):
        # Get the position of the match
        pos = match.start()
        
        # Look at the next few lines to determine the language
        next_lines = content[pos:pos+200].split('\n')
        if len(next_lines) > 1:
            first_line = next_lines[1].strip()
            
            # Determine language based on content
            if first_line.startswith('#'):
                if 'Confluence Configuration' in first_line:
                    return '```env\n'
                else:
                    return '```bash\n'
            elif first_line.startswith('git ') or first_line.startswith('python '):
                return '```bash\n'
            elif first_line.startswith('import ') or first_line.startswith('from '):
                return '```python\n'
            elif first_line.startswith('<') and '>' in first_line:
                return '```html\n'
            elif 'list all' in first_line or 'show me' in first_line or 'create a' in first_line or 'search for' in first_line:
                return '```text\n'
            else:
                return '```text\n'
        return '```text\n'
    
    # Replace code blocks
    updated_content = re.sub(pattern, replacement, content)
    
    # Write updated content back to file
    with open(file_path, 'w') as file:
        file.write(updated_content)
    
    print(f"Updated code blocks in {file_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "README.md"
    
    fix_code_blocks(file_path)

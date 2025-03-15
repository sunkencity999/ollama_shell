#!/usr/bin/env python3
"""
Script to fix the P4 priority issue in the Jira integration
"""

import re

# Path to the file
file_path = "/Users/christopher.bradford/ollamaShell/ollama_shell_jira_mcp.py"

# Read the file content
with open(file_path, 'r') as file:
    content = file.read()

# Replace the priority map definition to remove P4
pattern = r"'low': \[\\'\"Low Priority\"\\', \\'\"P4\"\\'\],"
replacement = "'low': [\\'\"Low Priority\"\\'],"

# Apply the replacement
modified_content = re.sub(pattern, replacement, content)

# Write the modified content back to the file
with open(file_path, 'w') as file:
    file.write(modified_content)

print("Successfully removed P4 from the priority mapping.")

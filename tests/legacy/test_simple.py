#!/usr/bin/env python3
import os
import sys
import json

# Print Python version and environment info
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# List files in the current directory
print("\nFiles in current directory:")
for file in os.listdir("."):
    print(f"- {file}")

# Test file creation
print("\nTesting file creation:")
test_file = os.path.expanduser("~/Documents/test_story.txt")
try:
    with open(test_file, "w") as f:
        f.write("This is a test story about a boy who loves ham sandwiches in Africa.")
    print(f"Successfully created file: {test_file}")
    
    # Read the file back
    with open(test_file, "r") as f:
        content = f.read()
    print(f"File content: {content}")
except Exception as e:
    print(f"Error: {str(e)}")

print("\nTest completed.")

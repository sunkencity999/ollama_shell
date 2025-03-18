#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run a simple test to check if file creation tasks are correctly identified
python3 -c "
import json
import sys

# Test task descriptions
tasks = [
    'Create a file with a short story about a boy who loves ham sandwiches in Africa',
    'Write a short story about a girl who discovers a magical tree in her backyard and save it to a file',
    'Search the web for information about climate change',
    'Create a document about the history of jazz music'
]

# Function to check if a task is a file creation task
def is_file_creation_task(task_lower):
    # Simple indicators
    file_creation_indicators = [
        'create a file', 'write a file', 'save to file', 'save a file',
        'write to file', 'save story', 'save text', 'create story',
        'write story', 'save document', 'create document'
    ]
    
    # Check for simple indicators
    if any(indicator in task_lower for indicator in file_creation_indicators):
        return True
    
    # More complex patterns
    if ('save' in task_lower and 'file' in task_lower) or \
       ('write' in task_lower and 'save' in task_lower) or \
       ('create' in task_lower and 'document' in task_lower) or \
       ('write' in task_lower and 'story' in task_lower):
        return True
    
    return False

# Check each task
print('Testing file creation task detection:')
for task in tasks:
    task_lower = task.lower()
    is_file_task = is_file_creation_task(task_lower)
    print(f'Task: \"{task}\"')
    print(f'Is file creation task: {is_file_task}')
    print('-' * 50)
"

# Deactivate the virtual environment
deactivate

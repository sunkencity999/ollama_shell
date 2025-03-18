#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the test script
python3 test_file_task.py

# Deactivate the virtual environment
deactivate

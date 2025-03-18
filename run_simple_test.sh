#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the simple file creation test script
python3 test_simple_file_creation.py

# Deactivate the virtual environment
deactivate

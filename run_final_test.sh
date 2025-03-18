#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the final test script
python3 final_file_test.py

# Deactivate the virtual environment
deactivate

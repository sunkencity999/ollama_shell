#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the updated assistant test script
python3 test_updated_assistant.py

# Deactivate the virtual environment
deactivate

#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the quick test script
python3 quick_test_venv.py

# Deactivate the virtual environment
deactivate

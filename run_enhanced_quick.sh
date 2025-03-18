#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the enhanced quick test script
python3 test_enhanced_quick.py

# Deactivate the virtual environment
deactivate

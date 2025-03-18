#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the enhanced integration test script
python3 test_enhanced_integration.py

# Deactivate the virtual environment
deactivate

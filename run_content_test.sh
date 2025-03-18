#!/bin/bash
# Activate the virtual environment
cd /Users/christopher.bradford/ollamaShell
source .venv/bin/activate

# Run the content generation test script
python3 test_content_generation.py

# Deactivate the virtual environment
deactivate

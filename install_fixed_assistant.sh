#!/bin/bash
# Script to install the fixed Agentic Assistant implementation

# Set the working directory
cd /Users/christopher.bradford/ollamaShell

# Create a backup of the original file
TIMESTAMP=$(date +%Y%m%d%H%M%S)
cp agentic_assistant.py agentic_assistant.py.$TIMESTAMP.bak
echo "Created backup at agentic_assistant.py.$TIMESTAMP.bak"

# Copy the updated implementation to the original file
cp updated_agentic_assistant.py agentic_assistant.py
echo "Installed fixed Agentic Assistant implementation"

# Copy the improved fixed file handler to the original file
cp fixed_file_handler_v2.py fixed_file_handler.py
chmod +x fixed_file_handler.py
echo "Installed improved fixed_file_handler.py"

# Display success message
echo "Installation complete!"
echo "The Agentic Assistant has been updated with improved file creation task handling."
echo "To test the changes, run the following command:"
echo "  ./run_updated_test.sh"

#!/bin/bash
#
# Ollama Shell Startup Script
# Created by Christopher Bradford
#
# This script provides a one-click solution to start the Ollama Shell application.
# It handles all necessary setup steps including:
# - Checking and starting the Ollama service
# - Setting up the Python virtual environment
# - Installing required dependencies
# - Launching the application
#

# Define color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the absolute path to the script's directory
# This ensures we can run the script from anywhere
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Set terminal size
if command -v resize &> /dev/null; then
    resize -s 50 150
else
    # Fallback to ANSI escape sequence
    printf '\e[8;50;150t'
fi

# Function: Check if a process is running
# Args: $1 - Process name or pattern to search for
# Returns: 0 if running, 1 if not running
is_process_running() {
    if pgrep -f "$1" >/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function: Display macOS notification
# Args: $1 - Notification title
#       $2 - Notification message
show_notification() {
    title="$1"
    message="$2"
    osascript -e "display notification \"$message\" with title \"$title\""
}

echo -e "${GREEN}Starting Ollama Shell...${NC}\n"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python is not installed! Please install Python 3.8 or higher.${NC}"
    echo -e "\nPress Enter to exit..."
    read -r
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install dependencies with verbose output
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -v -r requirements.txt

# Check if Ollama is installed
# If not, offer to install it using the official installer
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Ollama is not installed!${NC}"
    echo -e "${YELLOW}Would you like to install Ollama now? (y/n)${NC}"
    read -r install_ollama
    if [ "$install_ollama" = "y" ]; then
        echo -e "${GREEN}Installing Ollama...${NC}"
        curl https://ollama.ai/install.sh | sh
    else
        echo -e "${RED}Ollama is required to run this application.${NC}"
        echo -e "${YELLOW}Please install it from https://ollama.ai${NC}"
        echo -e "\nPress Enter to exit..."
        read -r
        exit 1
    fi
fi

# Check if Ollama service is running
# If not, start it and wait for it to be ready
if ! is_process_running "ollama serve"; then
    echo -e "${YELLOW}Ollama is not running. Starting Ollama...${NC}"
    show_notification "Ollama Shell" "Starting Ollama service..."
    
    # Start Ollama in the background, redirecting output to avoid clutter
    ollama serve &>/dev/null &
    
    # Wait for Ollama to start (max 30 seconds)
    # We check the API endpoint to ensure the service is fully ready
    max_attempts=30
    attempt=0
    while ! curl -s http://localhost:11434/api/tags &>/dev/null && [ $attempt -lt $max_attempts ]; do
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""
    
    # If we couldn't connect after max attempts, show error and exit
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}Failed to start Ollama service!${NC}"
        show_notification "Ollama Shell" "Failed to start Ollama service!"
        echo -e "\nPress Enter to exit..."
        read -r
        exit 1
    fi
    
    echo -e "${GREEN}Ollama service started successfully!${NC}"
    show_notification "Ollama Shell" "Ollama service started successfully!"
fi

# Ensure the main script is executable
chmod +x ollama_shell.py

# Clear the screen for a clean start
clear
echo -e "${GREEN}Starting Ollama Shell...${NC}\n"
show_notification "Ollama Shell" "Starting Ollama Shell..."

# Ensure Filesystem MCP Protocol server is available
echo -e "${YELLOW}Initializing Filesystem MCP Protocol server...${NC}"
# Start the server and wait for it to initialize (with a timeout)
python -c "from filesystem_mcp_integration import get_filesystem_mcp_integration; integration = get_filesystem_mcp_integration(); print('Filesystem MCP Protocol server ' + ('initialized successfully' if integration.available else 'failed to initialize'))"

# Launch the application
./ollama_shell.py

# Wait for user input before closing the window
# This ensures any error messages are visible
echo -e "\n${YELLOW}Ollama Shell has exited.${NC}"
echo -e "Press Enter to close this window..."
read -r

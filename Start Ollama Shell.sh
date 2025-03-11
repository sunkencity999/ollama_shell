#!/bin/bash

# Set terminal size
if command -v resize &> /dev/null; then
    resize -s 50 150
else
    # Fallback to ANSI escape sequence
    printf '\e[8;50;150t'
fi

echo "Starting Ollama Shell..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed! Please install Python 3.8 or higher."
    read -p "Press Enter to exit..."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade pip
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if Ollama service is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "Ollama service is not running!"
    
    # Check if systemd is available (Linux)
    if command -v systemctl &> /dev/null; then
        echo "Attempting to start Ollama service..."
        sudo systemctl start ollama
        sleep 2
        
        if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
            echo "Failed to start Ollama service."
            echo "Please ensure Ollama is installed and running."
            echo "Visit https://ollama.ai for installation instructions."
            read -p "Press Enter to exit..."
            exit 1
        fi
    else
        echo "Please ensure Ollama is installed and running."
        echo "Visit https://ollama.ai for installation instructions."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

# Ensure Filesystem MCP Protocol server is available
echo "Initializing Filesystem MCP Protocol server..."
# Start the server and wait for it to initialize (with a timeout)
python -c "from filesystem_mcp_integration import get_filesystem_mcp_integration; integration = get_filesystem_mcp_integration(); print('Filesystem MCP Protocol server ' + ('initialized successfully' if integration.available else 'failed to initialize'))"

# Start the application
python ollama_shell.py

# If there was an error, wait before closing
if [ $? -ne 0 ]; then
    echo
    echo "An error occurred. Press Enter to exit..."
    read
fi

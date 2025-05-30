#!/bin/bash

# Prevent running as root unless explicitly needed
if [ "$EUID" -eq 0 ]; then
    echo "This script should NOT be run as root (sudo). Please run as your normal user."
    exit 1
fi

# Set terminal size
if command -v resize &> /dev/null; then
    resize -s 50 150
else
    # Fallback to ANSI escape sequence
    printf '\e[8;50;150t'
fi

echo "Starting Ollama Shell..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed! Please install Python 3.8 or higher."
    read -p "Press Enter to exit..."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv || { echo "Failed to create virtual environment."; exit 1; }
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Failed to find venv/bin/activate. Virtual environment setup failed."
    exit 1
fi

# Install/upgrade pip
python3 -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed!"
    read -p "Would you like to install Ollama now? (y/n): " install_ollama
    if [ "$install_ollama" = "y" ]; then
        echo "Installing Ollama..."
        curl https://ollama.ai/install.sh | sh
        # Re-check if ollama is available after install
        if ! command -v ollama &> /dev/null; then
            echo "Ollama installation failed. Please install manually from https://ollama.ai"
            read -p "Press Enter to exit..."
            exit 1
        fi
    else
        echo "Ollama is required to run this application."
        echo "Please install it from https://ollama.ai"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

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

# Check if Docker is installed and set up Selenium WebDriver container for enhanced web browsing
if command -v docker &> /dev/null; then
    echo "Checking Selenium WebDriver container for enhanced web browsing..."
    
    # Check if the selenium/standalone-chrome container is already running
    if ! docker ps | grep -q selenium/standalone-chrome; then
        # Check if the container exists but is not running
        if docker ps -a | grep -q selenium/standalone-chrome; then
            echo "Starting existing Selenium container..."
            docker start $(docker ps -a | grep selenium/standalone-chrome | awk '{print $1}')
        else
            echo "Pulling Selenium WebDriver container image..."
            docker pull selenium/standalone-chrome:latest
            
            echo "Starting Selenium WebDriver container..."
            docker run -d -p 4444:4444 -p 7900:7900 --shm-size="2g" --name selenium-chrome selenium/standalone-chrome:latest
        fi
        
        # Wait for the container to be ready
        echo "Waiting for Selenium WebDriver container to be ready..."
        sleep 5
        
        echo "Selenium WebDriver container is ready!"
        echo "Enhanced web browsing capabilities are now available."
    else
        echo "Selenium WebDriver container is already running."
    fi
else
    echo "Docker is not installed. Enhanced web browsing capabilities will be limited."
    echo "To enable enhanced web browsing, please install Docker and run this script again."
fi

# Load environment variables for integrations
echo "Loading integration configurations..."

# Load Confluence configuration if available
if [ -f "Created Files/confluence_config.env" ]; then
    echo "Loading Confluence configuration..."
    set -a
    source "Created Files/confluence_config.env"
    set +a
    echo "Confluence configuration loaded successfully!"
    
    # Check if Ollama is running and get available models
    echo "Checking available Ollama models..."
    OLLAMA_RUNNING=false
    AVAILABLE_MODELS=""
    
    # Try to get available models from Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        OLLAMA_RUNNING=true
        AVAILABLE_MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d '"' -f 4 | tr '\n' ' ')
        echo "Available Ollama models: $AVAILABLE_MODELS"
    else
        echo "Ollama service not detected. Will check model availability when service starts."
    fi
    
    # Verify the analysis model is set
    if [ -z "$CONFLUENCE_ANALYSIS_MODEL" ]; then
        PREFERRED_MODEL="llama3.2:latest"
        echo "CONFLUENCE_ANALYSIS_MODEL not set in config"
        
        # If Ollama is running, check if preferred model is available
        if [ "$OLLAMA_RUNNING" = true ] && [[ " $AVAILABLE_MODELS " == *" $PREFERRED_MODEL "* ]]; then
            echo "Using preferred model: $PREFERRED_MODEL"
            export CONFLUENCE_ANALYSIS_MODEL="$PREFERRED_MODEL"
        elif [ "$OLLAMA_RUNNING" = true ] && [ ! -z "$AVAILABLE_MODELS" ]; then
            # Use first available model
            FIRST_MODEL=$(echo $AVAILABLE_MODELS | awk '{print $1}')
            echo "Preferred model not available. Using first available model: $FIRST_MODEL"
            export CONFLUENCE_ANALYSIS_MODEL="$FIRST_MODEL"
        else
            # Default to preferred model if Ollama isn't running or no models available
            echo "Setting default model: $PREFERRED_MODEL (will be verified when Ollama starts)"
            export CONFLUENCE_ANALYSIS_MODEL="$PREFERRED_MODEL"
        fi
    else
        # Model is set in config, but verify if it's available
        if [ "$OLLAMA_RUNNING" = true ]; then
            if [[ " $AVAILABLE_MODELS " == *" $CONFLUENCE_ANALYSIS_MODEL "* ]]; then
                echo "Using configured model: $CONFLUENCE_ANALYSIS_MODEL"
            else
                echo "Configured model '$CONFLUENCE_ANALYSIS_MODEL' not found in available models"
                
                # Check if preferred model is available
                PREFERRED_MODEL="llama3.2:latest"
                if [[ " $AVAILABLE_MODELS " == *" $PREFERRED_MODEL "* ]]; then
                    echo "Using preferred model: $PREFERRED_MODEL"
                    export CONFLUENCE_ANALYSIS_MODEL="$PREFERRED_MODEL"
                elif [ ! -z "$AVAILABLE_MODELS" ]; then
                    # Use first available model
                    FIRST_MODEL=$(echo $AVAILABLE_MODELS | awk '{print $1}')
                    echo "Using first available model: $FIRST_MODEL"
                    export CONFLUENCE_ANALYSIS_MODEL="$FIRST_MODEL"
                fi
            fi
        else
            echo "Using configured model: $CONFLUENCE_ANALYSIS_MODEL (will be verified when Ollama starts)"
        fi
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

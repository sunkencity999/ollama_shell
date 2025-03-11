#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing Ollama Shell...${NC}\n"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install requirements
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Ollama is not installed. Would you like to install it? (y/n)${NC}"
    read -r install_ollama
    if [ "$install_ollama" = "y" ]; then
        echo -e "${GREEN}Installing Ollama...${NC}"
        curl https://ollama.ai/install.sh | sh
    else
        echo -e "${YELLOW}Please install Ollama manually from https://ollama.ai${NC}"
    fi
fi

# Create necessary directories for user data
echo -e "${GREEN}Creating user data directories...${NC}"

# Create the Created Files directory and its subdirectories using both methods
# 1. Using mkdir (for bash environments)
mkdir -p "Created Files/jobs" "Created Files/datasets" "Created Files/models" "Created Files/exports"

# Install Filesystem MCP Protocol dependencies
echo -e "${GREEN}Installing Filesystem MCP Protocol dependencies...${NC}"
python install_filesystem_mcp_protocol.py

# 2. Using Python script (for cross-platform compatibility)
python3 create_directories.py

# Make ollama_shell.py executable
chmod +x ollama_shell.py

echo -e "\n${GREEN}Installation complete!${NC}"
echo -e "${GREEN}To start Ollama Shell:${NC}"
echo -e "1. Start Ollama: ${YELLOW}ollama serve${NC}"
echo -e "2. In a new terminal:"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo -e "   ${YELLOW}./ollama_shell.py${NC}"

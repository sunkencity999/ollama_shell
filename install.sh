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

# Guide users through optional Confluence integration setup
echo -e "\n${GREEN}Setting up optional integrations...${NC}"
echo -e "${YELLOW}Would you like to set up the Confluence integration? (y/n)${NC}"
read -r setup_confluence

if [ "$setup_confluence" = "y" ]; then
    echo -e "${GREEN}Setting up Confluence integration...${NC}"
    
    # Create config directory if it doesn't exist
    mkdir -p "Created Files/config"
    
    # Define template and config files
    template_file="Created Files/config/confluence_config_template.env"
    config_file="Created Files/confluence_config.env"
    
    # Create template file if it doesn't exist
    if [ ! -f "$template_file" ]; then
        cat > "$template_file" << EOL
# Confluence Configuration
# Fill in your Confluence details below

# Required settings
CONFLUENCE_URL=https://your-instance.atlassian.net
CONFLUENCE_EMAIL=your.email@example.com
CONFLUENCE_API_TOKEN=your_api_token_here

# Optional settings
CONFLUENCE_AUTH_METHOD=pat
CONFLUENCE_IS_CLOUD=true
CONFLUENCE_ANALYSIS_MODEL=llama3.2:latest
EOL
        echo -e "${GREEN}Created Confluence configuration template: $template_file${NC}"
    fi
    
    # Copy the template to the actual config file if it doesn't exist
    if [ ! -f "$config_file" ]; then
        cp "$template_file" "$config_file"
        echo -e "${GREEN}Created Confluence configuration file: $config_file${NC}"
    fi
        
        echo -e "${YELLOW}Please edit the configuration file at $config_file with your Confluence details.${NC}"
        echo -e "${YELLOW}You will need to provide:${NC}"
        echo -e "  - Confluence URL"
        echo -e "  - Your email/username"
        echo -e "  - Your Personal Access Token (PAT) or API token"
        echo -e "  - (Optional) Confluence analysis model (default: llama3.2:latest)"
        
        # Ask if they want to open the file now
        echo -e "${YELLOW}Would you like to open the configuration file now? (y/n)${NC}"
        read -r open_config
        
        if [ "$open_config" = "y" ]; then
            # Try to open with the default editor
            if [ -n "$EDITOR" ]; then
                $EDITOR "$config_file"
            elif command -v nano &> /dev/null; then
                nano "$config_file"
            elif command -v vim &> /dev/null; then
                vim "$config_file"
            else
                echo -e "${YELLOW}No text editor found. Please open $config_file manually.${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}Confluence configuration template not found. Please run the setup script again.${NC}"
    fi
fi

echo -e "\n${GREEN}Installation complete!${NC}"
echo -e "${GREEN}To start Ollama Shell:${NC}"
echo -e "1. Start Ollama: ${YELLOW}ollama serve${NC}"
echo -e "2. In a new terminal:"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo -e "   ${YELLOW}./ollama_shell.py${NC}"

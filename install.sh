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

# Check if Docker is installed (required for Selenium WebDriver)
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker is not installed. Docker is required for enhanced web browsing capabilities.${NC}"
    echo -e "${YELLOW}Would you like to install Docker? (y/n)${NC}"
    read -r install_docker
    if [ "$install_docker" = "y" ]; then
        echo -e "${GREEN}Installing Docker...${NC}"
        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS - provide instructions for Docker Desktop
            echo -e "${YELLOW}Please download and install Docker Desktop from: https://www.docker.com/products/docker-desktop/${NC}"
            echo -e "${YELLOW}After installation, please run this script again.${NC}"
            exit 0
        elif [[ "$(uname)" == "Linux" ]]; then
            # Linux - use convenience script
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            echo -e "${GREEN}Docker installed. You may need to log out and back in for group changes to take effect.${NC}"
        else
            echo -e "${YELLOW}Please install Docker manually from https://www.docker.com/products/docker-desktop/${NC}"
        fi
    else
        echo -e "${YELLOW}Enhanced web browsing capabilities will be limited without Docker.${NC}"
    fi
else
    echo -e "${GREEN}Docker is installed. Enhanced web browsing capabilities will be available.${NC}"
fi

# Create necessary directories for user data
echo -e "${GREEN}Creating user data directories...${NC}"

# Create the Created Files directory and its subdirectories using both methods
# 1. Using mkdir (for bash environments)
mkdir -p "Created Files/jobs" "Created Files/datasets" "Created Files/models" "Created Files/exports"

# Install Filesystem MCP Protocol dependencies
echo -e "${GREEN}Installing Filesystem MCP Protocol dependencies...${NC}"
python install_filesystem_mcp_protocol.py

# Set up Selenium WebDriver container for enhanced web browsing
if command -v docker &> /dev/null; then
    echo -e "${GREEN}Setting up Selenium WebDriver container for enhanced web browsing...${NC}"
    
    # Check if the selenium/standalone-chrome container is already running
    if ! docker ps | grep -q selenium/standalone-chrome; then
        # Check if the container exists but is not running
        if docker ps -a | grep -q selenium/standalone-chrome; then
            echo -e "${YELLOW}Starting existing Selenium container...${NC}"
            docker start $(docker ps -a | grep selenium/standalone-chrome | awk '{print $1}')
        else
            echo -e "${YELLOW}Pulling Selenium WebDriver container image...${NC}"
            docker pull selenium/standalone-chrome:latest
            
            echo -e "${YELLOW}Starting Selenium WebDriver container...${NC}"
            docker run -d -p 4444:4444 -p 7900:7900 --shm-size="2g" --name selenium-chrome selenium/standalone-chrome:latest
        fi
        
        # Wait for the container to be ready
        echo -e "${YELLOW}Waiting for Selenium WebDriver container to be ready...${NC}"
        sleep 5
        
        echo -e "${GREEN}Selenium WebDriver container is ready!${NC}"
        echo -e "${GREEN}Enhanced web browsing capabilities are now available.${NC}"
    else
        echo -e "${GREEN}Selenium WebDriver container is already running.${NC}"
    fi
else
    echo -e "${YELLOW}Docker is not installed. Enhanced web browsing capabilities will be limited.${NC}"
fi

# 2. Using Python script (for cross-platform compatibility)
python3 create_directories.py

# Install the Enhanced Agentic Assistant with fixed file creation handling
echo -e "${GREEN}Installing Enhanced Agentic Assistant with improved file creation handling...${NC}"

# Check if the fixed file handler exists
if [ -f "fixed_file_handler_v2.py" ]; then
    # Copy the improved fixed file handler
    cp fixed_file_handler_v2.py fixed_file_handler.py
    chmod +x fixed_file_handler.py
    echo -e "${GREEN}Installed improved file creation handling${NC}"
else
    # Create the fixed file handler from scratch
    echo -e "${GREEN}Creating fixed file handler...${NC}"
    cat > fixed_file_handler.py << 'EOL'
#!/usr/bin/env python3
"""
Fixed File Handler for Ollama Shell

This module provides a fixed implementation of the file creation task handling
for the Agentic Assistant with improved filename extraction.
"""
import os
import re
import logging
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_filename(task_description: str) -> Optional[str]:
    """
    Extract a filename from a task description.
    
    Args:
        task_description: The task description to extract a filename from
        
    Returns:
        The extracted filename or None if no filename was found
    """
    # Pattern 1: Match quoted filenames
    pattern1 = r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']'
    match1 = re.search(pattern1, task_description)
    
    # Pattern 2: Match "save as" or "save to" followed by a filename
    pattern2 = r'save\s+(?:it\s+)?(?:as|to)\s+["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'
    match2 = re.search(pattern2, task_description, re.IGNORECASE)
    
    # Pattern 3: Match "called" or "named" followed by a filename
    pattern3 = r'(?:called|named)\s+["\']?([^"\']+\.[a-zA-Z0-9]+)["\']?'
    match3 = re.search(pattern3, task_description, re.IGNORECASE)
    
    # Use the first match found
    if match1:
        return match1.group(1)
    elif match2:
        return match2.group(1)
    elif match3:
        return match3.group(1)
    
    # Fallback: Generate a filename based on the task description
    # This is used when no filename is specified in the task
    task_words = task_description.lower().split()
    
    # Try to extract a topic from the task description
    topic = None
    about_idx = task_description.lower().find('about')
    if about_idx != -1:
        # Extract the first noun after "about"
        words_after_about = task_description[about_idx + 6:].strip().split()
        if words_after_about:
            topic = words_after_about[0].strip('.,;:!?')
    
    # If we found a topic, use it as the filename
    if topic:
        return f"{topic}.txt"
    
    # Check if this is a document, story, poem, etc.
    content_type = None
    for word in ['document', 'story', 'poem', 'essay', 'report', 'note']:
        if word in task_words:
            content_type = word
            break
    
    # If we found a content type, use it as the filename
    if content_type:
        return f"{content_type}.txt"
    
    # Last resort: use a generic filename
    return "document.txt"

async def handle_file_creation(agentic_ollama, task_description: str) -> Dict[str, Any]:
    """
    Handle file creation tasks.
    
    Args:
        agentic_ollama: Instance of AgenticOllama
        task_description: Natural language description of the file to create
        
    Returns:
        Dict containing the file creation results
    """
    try:
        # Extract filename from task description if specified
        filename = extract_filename(task_description)
        
        # If a filename was found, modify the task to ensure it's used
        if filename:
            # Check if the task already has a "save as" or "save to" instruction
            if "save as" not in task_description.lower() and "save to" not in task_description.lower():
                # Add a "save as" instruction to the task
                task_description = f"{task_description} (Save as '{filename}')"
                
        # Use the create_file method from AgenticOllama
        result = await agentic_ollama.create_file(task_description)
        
        # Get the filename from the result
        filename = result.get('filename', 'unknown')
        
        # Format the result properly for task manager
        return {
            "success": True,
            "task_type": "file_creation",
            "result": {
                "filename": filename,
                "file_type": os.path.splitext(filename)[1] if filename != 'unknown' else '',
                "content_preview": result.get('content_preview', ''),
                "full_result": result
            },
            "message": f"Successfully created file: {filename}"
        }
    except Exception as e:
        logger.error(f"Error creating file: {str(e)}")
        return {
            "success": False,
            "task_type": "file_creation",
            "error": str(e),
            "message": f"Failed to create file: {str(e)}"
        }

def display_file_result(result: Dict[str, Any]) -> None:
    """
    Display a file creation result.
    
    Args:
        result: The file creation result to display
    """
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    file_result = result.get("result", {})
    
    # Check if we have a full_result field with more details
    full_result = file_result.get('full_result', {})
    
    # Get filename from the most reliable source
    filename = file_result.get('filename', 'unknown')
    if filename == 'unknown' and full_result:
        filename = full_result.get('filename', 'unknown')
    
    # Get content preview from the most reliable source
    content_preview = file_result.get('content_preview', '')
    if not content_preview and full_result:
        content_preview = full_result.get('content_preview', '')
    
    # Display the results
    console.print(f"[bold green]✓ {result.get('message', 'Task completed')}[/bold green]")
    console.print(f"[bold]File:[/bold] {filename}")
    console.print(f"[bold]Type:[/bold] {file_result.get('file_type', '')}")
    if content_preview:
        console.print("[bold]Content Preview:[/bold]")
        console.print(Panel(content_preview, border_style="blue"))
EOL
    chmod +x fixed_file_handler.py
    echo -e "${GREEN}Created fixed file handler${NC}"
fi

# Check if the updated agentic assistant exists
if [ -f "updated_agentic_assistant.py" ]; then
    # Create a backup of the original file
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    cp agentic_assistant.py agentic_assistant.py.$TIMESTAMP.bak
    echo -e "${GREEN}Created backup at agentic_assistant.py.$TIMESTAMP.bak${NC}"
    
    # Copy the updated implementation to the original file
    cp updated_agentic_assistant.py agentic_assistant.py
    echo -e "${GREEN}Installed fixed Agentic Assistant implementation${NC}"
else
    echo -e "${YELLOW}Updated Agentic Assistant not found. Using standard implementation.${NC}"
    echo -e "${YELLOW}File creation handling may not be optimal.${NC}"
fi

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

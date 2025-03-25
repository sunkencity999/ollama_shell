#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Testing Linux installation script...${NC}\n"

# Function to check if a command exists
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓ $1 is available${NC}"
        return 0
    else
        echo -e "${RED}✗ $1 is not available${NC}"
        return 1
    fi
}

# Function to check if a directory exists
check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓ Directory $1 exists${NC}"
        return 0
    else
        echo -e "${RED}✗ Directory $1 does not exist${NC}"
        return 1
    fi
}

# Function to check if a file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓ File $1 exists${NC}"
        return 0
    else
        echo -e "${RED}✗ File $1 does not exist${NC}"
        return 1
    fi
}

# Check for required commands
echo -e "\n${YELLOW}Checking for required commands...${NC}"
check_command python3
check_command pip
check_command curl

# Check for optional commands
echo -e "\n${YELLOW}Checking for optional commands...${NC}"
check_command ollama
check_command docker

# Check if the install script exists
echo -e "\n${YELLOW}Checking for installation script...${NC}"
check_file "install.sh"

# Check for required files
echo -e "\n${YELLOW}Checking for required files...${NC}"
check_file "requirements.txt"
check_file "ollama_shell.py"

# Create a temporary directory for testing
echo -e "\n${YELLOW}Creating temporary test directory...${NC}"
TEST_DIR="test_install_temp"
mkdir -p "$TEST_DIR"

# Test directory creation
echo -e "\n${YELLOW}Testing directory creation...${NC}"
mkdir -p "$TEST_DIR/Created Files/jobs" "$TEST_DIR/Created Files/datasets" "$TEST_DIR/Created Files/models" "$TEST_DIR/Created Files/exports" "$TEST_DIR/Created Files/config"

check_directory "$TEST_DIR/Created Files/jobs"
check_directory "$TEST_DIR/Created Files/datasets"
check_directory "$TEST_DIR/Created Files/models"
check_directory "$TEST_DIR/Created Files/exports"
check_directory "$TEST_DIR/Created Files/config"

# Test file creation
echo -e "\n${YELLOW}Testing file creation...${NC}"
touch "$TEST_DIR/Created Files/jobs/.gitkeep"
touch "$TEST_DIR/Created Files/datasets/.gitkeep"
touch "$TEST_DIR/Created Files/models/.gitkeep"
touch "$TEST_DIR/Created Files/exports/.gitkeep"
touch "$TEST_DIR/Created Files/config/.gitkeep"

check_file "$TEST_DIR/Created Files/jobs/.gitkeep"
check_file "$TEST_DIR/Created Files/datasets/.gitkeep"
check_file "$TEST_DIR/Created Files/models/.gitkeep"
check_file "$TEST_DIR/Created Files/exports/.gitkeep"
check_file "$TEST_DIR/Created Files/config/.gitkeep"

# Test config file creation
echo -e "\n${YELLOW}Testing config file creation...${NC}"
cat > "$TEST_DIR/Created Files/config/confluence_config_template.env" << EOL
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

check_file "$TEST_DIR/Created Files/config/confluence_config_template.env"

# Test Python virtual environment
echo -e "\n${YELLOW}Testing Python virtual environment creation...${NC}"
if python3 -m venv "$TEST_DIR/venv"; then
    echo -e "${GREEN}✓ Virtual environment created successfully${NC}"
    
    # Test activation
    echo -e "\n${YELLOW}Testing virtual environment activation...${NC}"
    if source "$TEST_DIR/venv/bin/activate" 2>/dev/null; then
        echo -e "${GREEN}✓ Virtual environment activated successfully${NC}"
        deactivate
    else
        echo -e "${RED}✗ Failed to activate virtual environment${NC}"
    fi
else
    echo -e "${RED}✗ Failed to create virtual environment${NC}"
fi

# Clean up
echo -e "\n${YELLOW}Cleaning up test directory...${NC}"
rm -rf "$TEST_DIR"
echo -e "${GREEN}✓ Test directory removed${NC}"

echo -e "\n${GREEN}Test completed!${NC}"
echo -e "${YELLOW}Note: This test only checks for basic functionality and environment readiness.${NC}"
echo -e "${YELLOW}To fully test the installation, you would need to run the actual install.sh script.${NC}"

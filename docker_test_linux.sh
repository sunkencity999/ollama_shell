#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Testing Linux installation script in Docker container...${NC}\n"

# Create a temporary Dockerfile for testing
cat > Dockerfile.test.linux << EOL
FROM ubuntu:22.04

# Install necessary packages
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-venv \\
    curl \\
    nano \\
    vim \\
    git

# Create a working directory
WORKDIR /app

# Copy only the essential files
COPY install.sh /app/
COPY requirements.txt /app/
COPY ollama_shell.py /app/

# Create dummy files for optional dependencies
RUN touch /app/create_directories.py
RUN touch /app/install_filesystem_mcp_protocol.py
RUN touch /app/fixed_file_handler_v2.py
RUN touch /app/updated_agentic_assistant.py
RUN touch /app/agentic_assistant.py

# Make the script executable
RUN chmod +x /app/install.sh
RUN chmod +x /app/ollama_shell.py 2>/dev/null || :

# Create a test script
RUN echo '#!/bin/bash' > /app/test_script.sh
RUN echo 'echo "Testing installation script..."' >> /app/test_script.sh
RUN echo 'echo "y" | bash /app/install.sh' >> /app/test_script.sh
RUN echo 'echo "Installation test completed."' >> /app/test_script.sh
RUN chmod +x /app/test_script.sh

# Set the entrypoint
ENTRYPOINT ["/app/test_script.sh"]
EOL

# Build the Docker image
echo -e "${YELLOW}Building Docker image for testing...${NC}"
docker build -t ollama-shell-test-linux -f Dockerfile.test.linux .

# Run the Docker container
echo -e "${YELLOW}Running test in Docker container...${NC}"
docker run --rm ollama-shell-test-linux

# Clean up
echo -e "${YELLOW}Cleaning up...${NC}"
rm Dockerfile.test.linux

echo -e "\n${GREEN}Docker-based test completed!${NC}"
echo -e "${YELLOW}Note: This test runs the install.sh script in a clean Ubuntu environment.${NC}"
echo -e "${YELLOW}It automatically answers 'y' to all prompts for non-interactive testing.${NC}"

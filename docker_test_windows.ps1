# PowerShell script to test Windows installation in a Docker container
# Note: This requires Docker Desktop with Windows containers enabled

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Green "Testing Windows installation script in Docker container..."
Write-Output ""

# Create a temporary Dockerfile for testing
@"
FROM mcr.microsoft.com/windows/servercore:ltsc2019

# Set working directory
WORKDIR C:\app

# Copy the installation script and necessary files
COPY install.bat C:\app\
COPY requirements.txt C:\app\
COPY ollama_shell.py C:\app\

# Create dummy files for optional dependencies
RUN echo. > C:\app\create_directories.py
RUN echo. > C:\app\install_filesystem_mcp_protocol.py
RUN echo. > C:\app\fixed_file_handler_v2.py
RUN echo. > C:\app\updated_agentic_assistant.py
RUN echo. > C:\app\agentic_assistant.py

# Create a test script
RUN echo @echo Testing installation script... > C:\app\test_script.bat
RUN echo @echo y | C:\app\install.bat >> C:\app\test_script.bat
RUN echo @echo Installation test completed. >> C:\app\test_script.bat

# Set the entrypoint
ENTRYPOINT ["cmd", "/c", "C:\\app\\test_script.bat"]
"@ | Out-File -Encoding ASCII -FilePath Dockerfile.test.windows

# Check if Docker is running in Windows container mode
$dockerInfo = docker info 2>&1
if ($dockerInfo -match "windows") {
    Write-ColorOutput Green "Docker is running in Windows container mode."
} else {
    Write-ColorOutput Red "Docker is not running in Windows container mode. Please switch to Windows containers."
    Write-ColorOutput Yellow "You can switch using the Docker Desktop tray icon > Switch to Windows containers..."
    exit 1
}

# Build the Docker image
Write-ColorOutput Yellow "Building Docker image for testing..."
docker build -t ollama-shell-test-windows -f Dockerfile.test.windows .

# Run the Docker container
Write-ColorOutput Yellow "Running test in Docker container..."
docker run --rm ollama-shell-test-windows

# Clean up
Write-ColorOutput Yellow "Cleaning up..."
Remove-Item Dockerfile.test.windows

Write-Output ""
Write-ColorOutput Green "Docker-based test completed!"
Write-ColorOutput Yellow "Note: This test runs the install.bat script in a clean Windows environment."
Write-ColorOutput Yellow "It automatically answers 'y' to all prompts for non-interactive testing."

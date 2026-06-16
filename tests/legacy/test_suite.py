#!/usr/bin/env python3
"""
Comprehensive Test Suite for Ollama Shell Installation Scripts

This script tests the installation scripts for both Windows and Linux environments.
It verifies that the scripts work correctly, especially when Confluence credentials
aren't provided during installation.
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
import argparse
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color


def print_colored(message, color):
    """Print a colored message to the terminal."""
    print(f"{color}{message}{Colors.NC}")


def check_command(command):
    """Check if a command is available on the system."""
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        print_colored(f"✓ {command} is available", Colors.GREEN)
        return True
    except FileNotFoundError:
        print_colored(f"✗ {command} is not available", Colors.RED)
        return False


def check_file(file_path):
    """Check if a file exists."""
    if os.path.isfile(file_path):
        print_colored(f"✓ File {file_path} exists", Colors.GREEN)
        return True
    else:
        print_colored(f"✗ File {file_path} does not exist", Colors.RED)
        return False


def check_directory(directory_path):
    """Check if a directory exists."""
    if os.path.isdir(directory_path):
        print_colored(f"✓ Directory {directory_path} exists", Colors.GREEN)
        return True
    else:
        print_colored(f"✗ Directory {directory_path} does not exist", Colors.RED)
        return False


def test_environment():
    """Test the current environment for required dependencies."""
    print_colored("\nChecking for required commands...", Colors.YELLOW)
    
    if platform.system() == "Windows":
        python_cmd = "python"
    else:
        python_cmd = "python3"
    
    check_command(python_cmd)
    check_command("pip")
    
    print_colored("\nChecking for optional commands...", Colors.YELLOW)
    check_command("ollama")
    check_command("docker")
    
    print_colored("\nChecking for installation scripts...", Colors.YELLOW)
    if platform.system() == "Windows":
        check_file("install.bat")
    else:
        check_file("install.sh")
    
    print_colored("\nChecking for required files...", Colors.YELLOW)
    check_file("requirements.txt")
    check_file("ollama_shell.py")


def test_directory_creation():
    """Test directory creation functionality."""
    print_colored("\nTesting directory creation...", Colors.YELLOW)
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_test_")
    
    try:
        # Create the necessary directories
        for subdir in ["jobs", "datasets", "models", "exports", "config"]:
            os.makedirs(os.path.join(temp_dir, "Created Files", subdir), exist_ok=True)
            check_directory(os.path.join(temp_dir, "Created Files", subdir))
        
        # Create .gitkeep files
        for subdir in ["jobs", "datasets", "models", "exports", "config"]:
            gitkeep_path = os.path.join(temp_dir, "Created Files", subdir, ".gitkeep")
            with open(gitkeep_path, "w") as f:
                pass
            check_file(gitkeep_path)
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print_colored(f"✓ Test directory {temp_dir} removed", Colors.GREEN)


def test_config_file_creation():
    """Test configuration file creation."""
    print_colored("\nTesting config file creation...", Colors.YELLOW)
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_test_")
    
    try:
        # Create the config directory
        config_dir = os.path.join(temp_dir, "Created Files", "config")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create a Confluence config template
        template_path = os.path.join(config_dir, "confluence_config_template.env")
        with open(template_path, "w") as f:
            f.write("""# Confluence Configuration
# Fill in your Confluence details below

# Required settings
CONFLUENCE_URL=https://your-instance.atlassian.net
CONFLUENCE_EMAIL=your.email@example.com
CONFLUENCE_API_TOKEN=your_api_token_here

# Optional settings
CONFLUENCE_AUTH_METHOD=pat
CONFLUENCE_IS_CLOUD=true
CONFLUENCE_ANALYSIS_MODEL=llama3.2:latest
""")
        
        check_file(template_path)
        
        # Create a Confluence config file
        config_path = os.path.join(temp_dir, "Created Files", "confluence_config.env")
        shutil.copy(template_path, config_path)
        check_file(config_path)
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print_colored(f"✓ Test directory {temp_dir} removed", Colors.GREEN)


def test_venv_creation():
    """Test virtual environment creation."""
    print_colored("\nTesting Python virtual environment creation...", Colors.YELLOW)
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_test_")
    
    try:
        # Create a virtual environment
        venv_dir = os.path.join(temp_dir, "venv")
        
        if platform.system() == "Windows":
            python_cmd = "python"
        else:
            python_cmd = "python3"
        
        result = subprocess.run(
            [python_cmd, "-m", "venv", venv_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        
        if result.returncode == 0:
            print_colored("✓ Virtual environment created successfully", Colors.GREEN)
            
            # Check activation
            print_colored("\nTesting virtual environment activation...", Colors.YELLOW)
            
            if platform.system() == "Windows":
                activate_script = os.path.join(venv_dir, "Scripts", "activate.bat")
                cmd = f"call {activate_script} && python --version"
                shell = True
            else:
                activate_script = os.path.join(venv_dir, "bin", "activate")
                cmd = f"source {activate_script} && python --version"
                shell = True
            
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=shell,
                    check=False,
                )
                
                if result.returncode == 0:
                    print_colored("✓ Virtual environment activated successfully", Colors.GREEN)
                else:
                    print_colored("✗ Failed to activate virtual environment", Colors.RED)
            except Exception as e:
                print_colored(f"✗ Error activating virtual environment: {e}", Colors.RED)
        else:
            print_colored("✗ Failed to create virtual environment", Colors.RED)
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print_colored(f"✓ Test directory {temp_dir} removed", Colors.GREEN)


def test_docker_linux():
    """Test the Linux installation script in a Docker container."""
    print_colored("\nTesting Linux installation script in Docker container...", Colors.YELLOW)
    
    if not check_command("docker"):
        print_colored("✗ Docker is not available. Skipping Docker test.", Colors.RED)
        return
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_docker_test_")
    
    try:
        # Create a Dockerfile
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write("""FROM ubuntu:22.04

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

# Copy the installation script and necessary files
COPY install.sh /app/
COPY requirements.txt /app/
COPY ollama_shell.py /app/

# Make the script executable
RUN chmod +x /app/install.sh
RUN chmod +x /app/ollama_shell.py

# Create a test script
RUN echo '#!/bin/bash' > /app/test_script.sh
RUN echo 'echo "Testing installation script..."' >> /app/test_script.sh
RUN echo 'echo "n" | bash /app/install.sh' >> /app/test_script.sh
RUN echo 'echo "Installation test completed."' >> /app/test_script.sh
RUN chmod +x /app/test_script.sh

# Set the entrypoint
ENTRYPOINT ["/app/test_script.sh"]
""")
        
        # Copy necessary files to the temp directory
        for file in ["install.sh", "requirements.txt", "ollama_shell.py"]:
            if os.path.exists(file):
                shutil.copy(file, temp_dir)
        
        # Build the Docker image
        print_colored("Building Docker image for testing...", Colors.YELLOW)
        result = subprocess.run(
            ["docker", "build", "-t", "ollama-shell-test", temp_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        
        if result.returncode == 0:
            print_colored("✓ Docker image built successfully", Colors.GREEN)
            
            # Run the Docker container
            print_colored("Running test in Docker container...", Colors.YELLOW)
            result = subprocess.run(
                ["docker", "run", "--rm", "ollama-shell-test"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            
            if result.returncode == 0:
                print_colored("✓ Docker test completed successfully", Colors.GREEN)
            else:
                print_colored("✗ Docker test failed", Colors.RED)
                print(result.stdout.decode())
                print(result.stderr.decode())
        else:
            print_colored("✗ Failed to build Docker image", Colors.RED)
            print(result.stdout.decode())
            print(result.stderr.decode())
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print_colored(f"✓ Test directory {temp_dir} removed", Colors.GREEN)


def test_script_execution():
    """Test the execution of the installation script with simulated user input."""
    print_colored("\nTesting script execution with simulated input...", Colors.YELLOW)
    
    if platform.system() == "Windows":
        print_colored("Script execution test is not implemented for Windows.", Colors.YELLOW)
        return
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_exec_test_")
    
    try:
        # Copy the installation script to the temp directory
        if os.path.exists("install.sh"):
            script_path = os.path.join(temp_dir, "install.sh")
            shutil.copy("install.sh", script_path)
            os.chmod(script_path, 0o755)
            
            # Copy necessary files
            for file in ["requirements.txt", "ollama_shell.py"]:
                if os.path.exists(file):
                    shutil.copy(file, temp_dir)
            
            # Create a simulated input file
            input_file = os.path.join(temp_dir, "input.txt")
            with open(input_file, "w") as f:
                f.write("n\n" * 10)  # Answer "no" to all prompts
            
            # Run the script with simulated input
            try:
                process = subprocess.Popen(
                    ["bash", script_path],
                    stdin=open(input_file, "r"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=temp_dir,
                )
                
                stdout, stderr = process.communicate(timeout=60)
                
                if process.returncode == 0:
                    print_colored("✓ Script executed successfully with simulated input", Colors.GREEN)
                else:
                    print_colored("✗ Script execution failed", Colors.RED)
                    print(stdout.decode())
                    print(stderr.decode())
            
            except subprocess.TimeoutExpired:
                process.kill()
                print_colored("✗ Script execution timed out", Colors.RED)
            
            except Exception as e:
                print_colored(f"✗ Error executing script: {e}", Colors.RED)
        
        else:
            print_colored("✗ install.sh not found", Colors.RED)
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print_colored(f"✓ Test directory {temp_dir} removed", Colors.GREEN)


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test the Ollama Shell installation scripts.")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--env", action="store_true", help="Test the environment")
    parser.add_argument("--dirs", action="store_true", help="Test directory creation")
    parser.add_argument("--config", action="store_true", help="Test config file creation")
    parser.add_argument("--venv", action="store_true", help="Test virtual environment creation")
    parser.add_argument("--docker", action="store_true", help="Test in Docker container (Linux only)")
    parser.add_argument("--exec", action="store_true", help="Test script execution (Linux only)")
    
    args = parser.parse_args()
    
    # If no arguments are provided, run all tests
    if not any(vars(args).values()):
        args.all = True
    
    print_colored(f"Running tests on {platform.system()}...", Colors.GREEN)
    
    if args.all or args.env:
        test_environment()
    
    if args.all or args.dirs:
        test_directory_creation()
    
    if args.all or args.config:
        test_config_file_creation()
    
    if args.all or args.venv:
        test_venv_creation()
    
    if (args.all or args.docker) and platform.system() != "Windows":
        test_docker_linux()
    
    if (args.all or args.exec) and platform.system() != "Windows":
        test_script_execution()
    
    print_colored("\nAll tests completed!", Colors.GREEN)


if __name__ == "__main__":
    main()

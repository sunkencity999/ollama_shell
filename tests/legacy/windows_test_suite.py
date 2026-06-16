#!/usr/bin/env python3
"""
Windows-specific Test Suite for Ollama Shell Installation

This script provides comprehensive testing for the Windows installation script.
It can be run on a Windows system to verify that the installation script works correctly,
especially when Confluence credentials aren't provided.
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
    if platform.system() == "Windows":
        # Windows command prompt doesn't support ANSI colors by default
        print(message)
    else:
        print(f"{color}{message}{Colors.NC}")


def check_command(command):
    """Check if a command is available on the system."""
    try:
        if platform.system() == "Windows":
            # Use 'where' on Windows
            result = subprocess.run(
                ["where", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode == 0:
                print_colored(f"✓ {command} is available", Colors.GREEN)
                return True
            else:
                print_colored(f"✗ {command} is not available", Colors.RED)
                return False
        else:
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


def test_windows_environment():
    """Test the Windows environment for required dependencies."""
    if platform.system() != "Windows":
        print_colored("This test is designed for Windows systems only.", Colors.RED)
        return False
    
    print_colored("\nChecking for required commands...", Colors.YELLOW)
    
    python_available = check_command("python")
    pip_available = check_command("pip")
    
    print_colored("\nChecking for optional commands...", Colors.YELLOW)
    check_command("ollama")
    check_command("docker")
    
    print_colored("\nChecking for installation scripts...", Colors.YELLOW)
    install_bat_exists = check_file("install.bat")
    
    print_colored("\nChecking for required files...", Colors.YELLOW)
    requirements_exists = check_file("requirements.txt")
    ollama_shell_exists = check_file("ollama_shell.py")
    
    return python_available and pip_available and install_bat_exists and requirements_exists and ollama_shell_exists


def test_windows_directory_creation():
    """Test directory creation functionality on Windows."""
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


def test_windows_config_file_creation():
    """Test configuration file creation on Windows."""
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


def test_windows_venv_creation():
    """Test virtual environment creation on Windows."""
    print_colored("\nTesting Python virtual environment creation...", Colors.YELLOW)
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_test_")
    
    try:
        # Create a virtual environment
        venv_dir = os.path.join(temp_dir, "venv")
        
        result = subprocess.run(
            ["python", "-m", "venv", venv_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        
        if result.returncode == 0:
            print_colored("✓ Virtual environment created successfully", Colors.GREEN)
            
            # Check activation
            print_colored("\nTesting virtual environment activation...", Colors.YELLOW)
            
            activate_script = os.path.join(venv_dir, "Scripts", "activate.bat")
            cmd = f"call {activate_script} && python --version"
            
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
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


def test_windows_script_execution():
    """Test the execution of the Windows installation script with simulated user input."""
    print_colored("\nTesting script execution with simulated input...", Colors.YELLOW)
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="ollama_shell_exec_test_")
    
    try:
        # Copy the installation script to the temp directory
        if os.path.exists("install.bat"):
            script_path = os.path.join(temp_dir, "install.bat")
            shutil.copy("install.bat", script_path)
            
            # Copy necessary files
            for file in ["requirements.txt", "ollama_shell.py"]:
                if os.path.exists(file):
                    shutil.copy(file, temp_dir)
            
            # Create a simulated input file (not directly usable with batch files)
            # Instead, we'll create a wrapper script
            wrapper_path = os.path.join(temp_dir, "test_wrapper.bat")
            with open(wrapper_path, "w") as f:
                f.write("""@echo off
echo Testing installation script...
echo n | call install.bat
echo Test completed.
""")
            
            # Run the wrapper script
            try:
                process = subprocess.Popen(
                    [wrapper_path],
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
            print_colored("✗ install.bat not found", Colors.RED)
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print_colored(f"✓ Test directory {temp_dir} removed", Colors.GREEN)


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test the Ollama Shell Windows installation script.")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--env", action="store_true", help="Test the environment")
    parser.add_argument("--dirs", action="store_true", help="Test directory creation")
    parser.add_argument("--config", action="store_true", help="Test config file creation")
    parser.add_argument("--venv", action="store_true", help="Test virtual environment creation")
    parser.add_argument("--exec", action="store_true", help="Test script execution")
    
    args = parser.parse_args()
    
    # If no arguments are provided, run all tests
    if not any(vars(args).values()):
        args.all = True
    
    if platform.system() != "Windows":
        print_colored("This test suite is designed for Windows systems only.", Colors.RED)
        print_colored("Please run this script on a Windows machine.", Colors.RED)
        return
    
    print_colored(f"Running Windows tests...", Colors.GREEN)
    
    if args.all or args.env:
        test_windows_environment()
    
    if args.all or args.dirs:
        test_windows_directory_creation()
    
    if args.all or args.config:
        test_windows_config_file_creation()
    
    if args.all or args.venv:
        test_windows_venv_creation()
    
    if args.all or args.exec:
        test_windows_script_execution()
    
    print_colored("\nAll Windows tests completed!", Colors.GREEN)


if __name__ == "__main__":
    main()

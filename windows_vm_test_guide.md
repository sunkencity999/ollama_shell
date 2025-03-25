# Testing Ollama Shell Installation on Windows

This guide provides instructions for testing the Ollama Shell Windows installation script (`install.bat`) in a Windows environment.

## Option 1: Testing in a Windows Virtual Machine

The most reliable way to test the Windows installation script is to use a Windows virtual machine:

1. **Set up a Windows VM**:
   - Use VirtualBox, VMware, Parallels, or any other virtualization software
   - Install a clean Windows 10 or Windows 11 system

2. **Prepare the VM**:
   - Copy the Ollama Shell repository to the VM
   - Ensure Python is installed (the script will attempt to install it if missing)

3. **Run the test script**:
   ```cmd
   test_install_windows.bat
   ```

4. **Run the actual installation**:
   ```cmd
   install.bat
   ```
   - When prompted about Confluence integration, select "n" to test the script's ability to continue without Confluence credentials

## Option 2: Testing with Docker Windows Containers (Windows Host Only)

If you have a Windows machine with Docker Desktop installed, you can use Windows containers:

1. **Switch to Windows containers**:
   - Right-click the Docker Desktop icon in the system tray
   - Select "Switch to Windows containers..."

2. **Run the PowerShell test script**:
   ```powershell
   .\docker_test_windows.ps1
   ```

This script will:
- Create a Windows container
- Copy the installation files
- Run the installation script
- Report the results

## Option 3: Remote Testing Service

You can use a remote Windows testing service:

1. **GitHub Actions**:
   - Create a GitHub workflow that runs on Windows runners
   - Add steps to execute the installation script
   - Check the exit code and output logs

2. **Azure DevOps Pipelines**:
   - Set up a pipeline with Windows agents
   - Configure it to run the test script
   - Collect and analyze the results

## Manual Testing Checklist

When testing the Windows installation script, verify that:

1. **Python environment**:
   - Python is installed or the script offers to install it
   - Virtual environment is created correctly
   - Dependencies are installed properly

2. **Directory structure**:
   - All required directories are created
   - `.gitkeep` files are added to empty directories

3. **Optional integrations**:
   - The script continues successfully when Confluence integration is skipped
   - The script continues successfully when Jira integration is skipped

4. **Final setup**:
   - The script completes without errors
   - The application can be launched after installation

## Troubleshooting Windows Installation

If you encounter issues during testing:

1. **Permission errors**:
   - Run Command Prompt or PowerShell as Administrator

2. **Python installation issues**:
   - Install Python manually from python.org
   - Ensure "Add Python to PATH" is selected during installation

3. **Virtual environment errors**:
   - Try creating the virtual environment manually:
     ```cmd
     python -m venv venv
     ```

4. **Dependency installation failures**:
   - Update pip before installing dependencies:
     ```cmd
     venv\Scripts\python -m pip install --upgrade pip
     ```

## Reporting Test Results

When reporting test results, include:

1. Windows version and build number
2. Python version
3. Complete console output
4. Screenshots of any error messages
5. Steps to reproduce any issues

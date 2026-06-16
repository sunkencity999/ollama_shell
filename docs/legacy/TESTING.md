# Testing Ollama Shell Installation Scripts

This document provides instructions for testing the Ollama Shell installation scripts in both Windows and Linux environments.

## Available Test Scripts

We've created several test scripts to verify that the installation process works correctly:

1. **Basic Test Suite** (`test_suite.py`): A Python script that tests various aspects of the installation process.
2. **Linux Test Script** (`test_install_linux.sh`): A shell script that tests the Linux installation process.
3. **Windows Test Script** (`test_install_windows.bat`): A batch script that tests the Windows installation process.
4. **Docker-based Linux Test** (`docker_test_linux.sh`): A script that tests the Linux installation in a Docker container.

## Running the Tests

### Basic Test Suite

The basic test suite can be run on any platform with Python installed:

```bash
# Run all tests
python test_suite.py --all

# Run specific tests
python test_suite.py --env --dirs --config
```

Available test options:
- `--env`: Test the environment (Python, pip, etc.)
- `--dirs`: Test directory creation
- `--config`: Test configuration file creation
- `--venv`: Test virtual environment creation
- `--docker`: Test in Docker container (Linux only)
- `--exec`: Test script execution (Linux only)

### Linux Test Script

On Linux or macOS, you can run the Linux test script:

```bash
# Make the script executable
chmod +x test_install_linux.sh

# Run the test
./test_install_linux.sh
```

### Windows Test Script

On Windows, you can run the Windows test script:

```cmd
# Run the test
test_install_windows.bat
```

### Docker-based Linux Test

This test runs the Linux installation script in a Docker container, which provides a clean environment for testing:

```bash
# Make the script executable
chmod +x docker_test_linux.sh

# Run the test
./docker_test_linux.sh
```

## Testing in Different Environments

### Testing on Linux

1. **Native Testing**:
   ```bash
   ./test_install_linux.sh
   ```

2. **Docker-based Testing**:
   ```bash
   ./docker_test_linux.sh
   ```

3. **Comprehensive Testing**:
   ```bash
   python test_suite.py --all
   ```

### Testing on Windows

1. **Native Testing**:
   ```cmd
   test_install_windows.bat
   ```

2. **Comprehensive Testing**:
   ```cmd
   python test_suite.py --env --dirs --config --venv
   ```

## Testing Without Confluence Credentials

The installation scripts have been designed to work properly even when Confluence credentials aren't provided. To test this scenario:

1. **Using the Docker Test**:
   The Docker test automatically answers "n" to the Confluence integration setup prompt.

2. **Manual Testing**:
   When running the installation scripts manually, simply answer "n" when prompted to set up the Confluence integration.

## Verifying the Installation

After running the installation script, you can verify that the installation was successful by:

1. **Checking for the virtual environment**:
   ```bash
   # Linux/macOS
   ls -la venv/

   # Windows
   dir venv
   ```

2. **Checking for the created directories**:
   ```bash
   # Linux/macOS
   ls -la "Created Files"/

   # Windows
   dir "Created Files"
   ```

3. **Testing the Ollama Shell application**:
   ```bash
   # Linux/macOS
   source venv/bin/activate
   ./ollama_shell.py --version

   # Windows
   call venv\Scripts\activate.bat
   python ollama_shell.py --version
   ```

## Troubleshooting

If you encounter issues during testing:

1. **Check the logs**: The test scripts output detailed logs that can help identify issues.

2. **Check dependencies**: Ensure that all required dependencies (Python, pip, etc.) are installed.

3. **Check permissions**: Ensure that you have the necessary permissions to create directories and files.

4. **Docker issues**: If the Docker test fails, ensure that Docker is installed and running.

5. **Virtual environment issues**: If the virtual environment creation fails, try creating it manually:
   ```bash
   # Linux/macOS
   python3 -m venv venv

   # Windows
   python -m venv venv
   ```

## Contributing

If you find issues with the installation scripts or test scripts, please submit a bug report or pull request.

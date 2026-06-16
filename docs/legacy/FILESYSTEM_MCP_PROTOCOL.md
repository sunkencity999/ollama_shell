# Filesystem MCP Protocol for Ollama Shell

This document explains how to use the Filesystem MCP Protocol integration with Ollama Shell, which allows LLMs to interact with the local filesystem using natural language commands.

## Overview

The Filesystem MCP Protocol integration enables Ollama Shell to use the Model Context Protocol (MCP) to provide LLMs with the ability to perform filesystem operations through natural language. This allows users to ask the LLM to perform tasks like:

- Listing files and directories
- Reading and writing files
- Creating directories
- Analyzing text files
- Finding duplicate files
- Creating and extracting ZIP archives

All of these operations can be performed using natural language commands in the chat interface, making it easier for users to work with files without leaving Ollama Shell.

## Installation

To install the Filesystem MCP Protocol integration, run the installation script:

```bash
python install_filesystem_mcp_protocol.py
```

This script will install the necessary dependencies:

1. MCP Python SDK (`pip install mcp`)
2. FastAPI and Uvicorn (`pip install fastapi uvicorn`)

## Components

The Filesystem MCP Protocol integration consists of several components:

1. **Filesystem MCP Protocol Server** (`filesystem_mcp_protocol.py`): An MCP server that exposes filesystem operations as resources and tools.

2. **Filesystem MCP Integration** (`filesystem_mcp_integration.py`): A client that connects to the MCP server and provides methods for executing natural language commands.

3. **Ollama Shell Filesystem MCP** (`ollama_shell_filesystem_mcp.py`): Integration with Ollama Shell that allows users to interact with the filesystem using natural language through the chat interface.

4. **Demo Script** (`demo_filesystem_mcp.py`): A standalone demo script that demonstrates how to use the Filesystem MCP Protocol integration.

## Usage

### Using the Demo Script

The demo script provides a simple way to test the Filesystem MCP Protocol integration:

```bash
python demo_filesystem_mcp.py --api-key YOUR_ANTHROPIC_API_KEY
```

You can also set the `ANTHROPIC_API_KEY` environment variable instead of using the `--api-key` argument:

```bash
export ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
python demo_filesystem_mcp.py
```

The demo script will start an interactive session where you can enter natural language commands to interact with the filesystem.

### Example Commands

Here are some example natural language commands you can use:

- "List all files in my home directory"
- "Create a new directory called 'test' in my Documents folder"
- "Read the content of the file README.md"
- "Write 'Hello, world!' to a new file called hello.txt"
- "Find all duplicate files in my Downloads folder"
- "Create a ZIP archive of my project files"
- "Analyze the text file essay.txt and tell me how many words it contains"

### Integration with Ollama Shell

The Filesystem MCP Protocol integration is automatically available in Ollama Shell. You can use it by sending natural language commands in the chat interface.

To use the integration, you need to:

1. Make sure the Filesystem MCP Protocol server is running (it will be started automatically if needed)
2. Set your Anthropic API key in Ollama Shell
3. Send natural language commands to interact with the filesystem

## Security

The Filesystem MCP Protocol server includes security measures to prevent unauthorized access to sensitive files:

1. **Allowed Paths**: The server only allows access to paths specified in the configuration.
2. **Path Validation**: All paths are validated to ensure they are allowed before any operation is performed.
3. **Error Handling**: Errors are properly handled and reported to prevent information leakage.

## Testing

To test the Filesystem MCP Protocol integration, run the test script:

```bash
python test_filesystem_mcp_protocol.py
```

This script will run a series of tests to verify that the integration works correctly.

## Troubleshooting

If you encounter issues with the Filesystem MCP Protocol integration, check the following:

1. Make sure the MCP Python SDK is installed (`pip install mcp`)
2. Make sure the Filesystem MCP Protocol server is running
3. Check the logs for error messages
4. Verify that your Anthropic API key is valid

## Limitations

The Filesystem MCP Protocol integration has the following limitations:

1. It requires an Anthropic API key to use the Claude models
2. It only allows access to paths specified in the configuration
3. It does not support all filesystem operations (e.g., moving or renaming files)

## Future Improvements

Planned improvements for the Filesystem MCP Protocol integration include:

1. Support for more filesystem operations (move, rename, copy)
2. Integration with more LLM providers (OpenAI, Gemini)
3. Enhanced security features
4. Better error handling and user feedback
5. Performance optimizations

## Contributing

Contributions to the Filesystem MCP Protocol integration are welcome! Please feel free to submit pull requests or open issues for bugs or feature requests.

## License

The Filesystem MCP Protocol integration is released under the same license as Ollama Shell.

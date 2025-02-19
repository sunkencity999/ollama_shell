# Ollama Shell

A powerful and user-friendly command line interface for Ollama, featuring a beautiful retro-style UI and advanced features for model management and chat interactions.

Created by Christopher Bradford

## Features

- 🤖 Interactive Chat Sessions
  - Multi-turn conversations with any Ollama model
  - System prompt support
  - Document context integration:
    - Drag-and-drop files directly into chat (toggle with Ctrl+V)
    - Support for PDF, Word, and text files
    - Automatic content extraction and analysis
  - Chat history management
  - Enhanced web search integration (prefix any query with "search:")

- 📚 Model Management
  - List available models
  - Download new models
  - Delete installed models
  - Model information display (size, modified date, digest)

- 🔍 Enhanced Search
  - Web search integration with DuckDuckGo
  - Automatic content analysis from search results
  - Source attribution and links
  - Comprehensive summaries

- ⚙️ Configuration
  - Customizable settings
  - Temperature and context length control
  - History saving options
  - Display preferences

- 📄 Document Support
  - PDF files
  - Word documents (.docx, .doc)
  - Text files (.txt, .md)
  - Code files (.py, .js, .html, .css, .json, .yaml)

  Files can be:
  - Dragged directly into the chat (toggle with Ctrl+V)
  - Specified as context when starting a chat
  - Referenced during conversation for analysis

- 🎨 Beautiful UI
  - Retro-style ASCII art
  - Color-coded outputs
  - Interactive menus
  - Progress indicators
  - Download and operation status tracking

## Installation

### Prerequisites
- Python 3.8 or higher
- Ollama (install from [ollama.ai](https://ollama.ai))

### Easy Install (All Platforms)

1. **macOS**:
   - Download and extract the zip file
   - Double-click `Start Ollama Shell.command`
   - The script will handle everything automatically

2. **Linux**:
   - Download and extract the zip file
   - Open terminal in the extracted directory
   - Make the startup script executable:
     ```bash
     chmod +x "Start Ollama Shell.sh"
     ```
   - Run the script:
     ```bash
     ./Start\ Ollama\ Shell.sh
     ```

3. **Windows**:
   - Download and extract the zip file
   - Double-click `Start Ollama Shell.bat`
   - The script will handle everything automatically

The startup scripts will:
- Check if Python is installed
- Create a virtual environment if needed
- Install/upgrade all dependencies
- Verify the Ollama service is running
- Start the application

### Manual Installation

### macOS

1. Easy Install (Recommended):
   - Download and extract the zip file
   - Double-click `Start Ollama Shell.command`
   - The script will automatically:
     - Install Ollama if needed
     - Start the Ollama service
     - Set up the Python environment
     - Install dependencies
     - Launch the application

2. Manual Install:
   ```bash
   # Install Ollama
   curl https://ollama.ai/install.sh | sh
   
   # Clone the repository
   git clone https://github.com/sunkencity999/ollama_shell
   cd ollamaShell
   
   # Run the install script
   ./install.sh
   ```

### Linux

1. Install Ollama:
   ```bash
   curl https://ollama.ai/install.sh | sh
   sudo systemctl start ollama
   ```

2. Install Python dependencies:
   ```bash
   # Clone the repository
   git clone https://github.com/sunkencity999/ollama_shell
   cd ollamaShell
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install duckduckgo-search beautifulsoup4 html2text
   ```

3. Start the application:
   ```bash
   ./ollama_shell.py
   ```

### Windows

1. Install Ollama:
   - Install WSL2 if not already installed
   - Follow the Windows installation instructions at [ollama.com](https://ollama.com)

2. Install Python:
   - Download Python 3.8+ from [python.org](https://python.org)
   - Make sure to check "Add Python to PATH" during installation

3. Install the application:
   ```powershell
   # Clone the repository
   git clone https://github.com/sunkencity999/ollama_shell
   cd ollamaShell
   
   # Create virtual environment
   python -m venv venv
   .\venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install duckduckgo-search beautifulsoup4 html2text
   ```

4. Start the application:
   ```powershell
   python ollama_shell.py
   ```

## Usage

### Quick Start
1. Make sure Ollama is running
2. Start the application:
   - macOS: Double-click `Start Ollama Shell.command`
   - Linux/Windows: Run `./ollama_shell.py` or `python ollama_shell.py`
3. Select a command from the menu by entering its number

### Basic Commands
- `chat`: Start an interactive chat session
  - Use Ctrl+V to toggle drag-and-drop mode for files
  - Simply drag any supported file into the terminal when in drag-and-drop mode
  - The file content will be automatically processed and included in your conversation
- `models`: List installed models
- `pull`: Download a new model
- `delete`: Remove an installed model
- `prompt`: Send a single prompt
- `history`: View chat history
- `settings`: Configure application settings
- `help`: Show detailed help

### Enhanced Search
During a chat session, you can use the enhanced search feature by prefixing your query with "search:". For example:
```
You: search: what is the current weather in San Francisco?
```

The system will:
1. Search the web using DuckDuckGo
2. Analyze multiple sources
3. Provide a comprehensive summary
4. List all sources used

This feature is particularly useful for:
- Getting up-to-date information
- Research queries
- Fact-checking
- Gathering multiple perspectives on a topic

The best part about the enhanced search feature is that it allows your LLM to have real-time information and analysis, making it a powerful tool for research and information gathering.

### Using Document Context
1. Start a chat session
2. When prompted, choose to include documents
3. Enter the path to each document
4. The documents' content will be available to the model during chat

### Configuration
The `config.json` file stores your preferences:
```json
{
  "default_model": "llama2",
  "temperature": 0.7,
  "context_length": 4096,
  "save_history": true,
  "history_file": "~/.ollama_shell_history",
  "verbose": false
}
```

## Troubleshooting

### Common Issues

1. "Ollama is not running"
   - macOS: `ollama serve`
   - Linux: `sudo systemctl start ollama`
   - Windows: Start Ollama from WSL2

2. "Model not found"
   - Run `./ollama_shell.py pull <model_name>`
   - Check available models at [ollama.com/library](https://ollama.com/library)

3. "Permission denied"
   - Make scripts executable:
     ```bash
     chmod +x ollama_shell.py
     chmod +x install.sh
     ```

4. "Dependencies not found"
   - Activate virtual environment:
     ```bash
     source venv/bin/activate  # Unix/macOS
     .\venv\Scripts\activate   # Windows
     ```
   - Reinstall dependencies:
     ```bash
     pip install -r requirements.txt
     pip install duckduckgo-search beautifulsoup4 html2text
     ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Standard MIT License

## Credits

Created by Christopher Bradford

Special thanks to:
- The Ollama team for their excellent LLM runtime
- The Python community for the amazing libraries used in this project

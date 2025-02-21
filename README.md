# Ollama Shell

<p align="center">
  <img src="resources/ollama_shell_logo.png" alt="Ollama Shell Logo" width="200"/>
</p>

A powerful interactive shell for Ollama, featuring enhanced chat capabilities, document analysis, image analysis, and real-time web search integration.

Created by Christopher Bradford
Contact: contact@christopherdanielbradford.com

## Features

### Core Features
- Interactive chat with any Ollama model
- Model management (download, delete, list)
- System prompt management and storage
- Chat history with export capabilities (Markdown, HTML, PDF)
- Configurable settings and preferences

### Advanced Features
- 🔍 **Enhanced Search & Analysis**: Real-time web search integration with DuckDuckGo
- 🖼️ **Image Analysis**: Support for analyzing images using vision models
- 📄 **Document Analysis**: Support for various document formats
- 🌐 **Real-time Information**: Combine search results with model analysis
- 💾 **Export Capabilities**: Export chats in multiple formats
- ⚡ **Drag & Drop**: Easy file sharing in chat

## Quick Start

### Windows Installation
1. Run `install_windows.bat` to set up the virtual environment and install dependencies
2. Run `run_ollama_shell.bat` to start the application

### Unix/Mac Installation
1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Unix/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python ollama_shell.py
```

## Tutorial

### Enhanced Search Queries
The Enhanced Search feature allows you to combine real-time web information with model analysis:

1. **Basic Search**:
   ```
   search: What are the latest developments in AI?
   ```
   This will search the web and provide an analyzed summary.

2. **Focused Questions**:
   ```
   search: Who won the latest Super Bowl and what was the score?
   ```
   Gets real-time information and provides accurate, up-to-date answers.

3. **Technical Queries**:
   ```
   search: How to implement rate limiting in Python?
   ```
   Combines web search results with model expertise for comprehensive answers.

### Image Analysis
Analyze images using vision models:

1. **From Menu**:
   - Select "Analyze Image" from the menu
   - Enter the path to your image
   - Optionally provide a custom prompt

2. **Drag & Drop**:
   - Press Ctrl+V to toggle drag & drop mode
   - Drag an image file into the terminal
   - The vision model will analyze the image

3. **In Chat Context**:
   - Images can be included in chat for analysis
   - Supported formats: JPG, PNG, GIF, BMP, WebP

### Document Analysis
Analyze various document types:

1. **Supported Formats**:
   - Word Documents (.docx, .doc)
   - PDF Files (.pdf)
   - Text Files (.txt, .md, etc.)
   - Code Files (.py, .js, etc.)

2. **Usage**:
   - Drag & drop documents into chat
   - Reference documents in prompts
   - Include multiple documents for context

## Supported File Formats

### Documents
- 📝 Word Documents (.docx, .doc)
- 📄 PDF Files (.pdf)
- ✍️ Text Files (.txt, .md)
- 💻 Code Files (.py, .js, .html, .css, .json, .yaml, .yml)

### Images
- 🖼️ JPEG/JPG
- 🎨 PNG
- 🎭 GIF
- 🖌️ BMP
- 🌅 WebP

### Export Formats
- 📝 Markdown
- 🌐 HTML
- 📑 PDF

## Dependencies
- Python 3.8+
- Ollama with compatible models
- See `requirements.txt` for full list

## Configuration
Configuration is stored in `config.json` and includes:
- Default model settings
- Vision model preferences
- History and logging preferences
- UI customization options

## Tips & Tricks
- Use `Ctrl+V` to toggle drag & drop mode
- Combine search and document analysis for comprehensive answers
- Save frequently used prompts for quick access
- Export important conversations for future reference
- Use custom prompts with image analysis for specific insights

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
MIT License - See LICENSE file for details

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
- 🧠 **Context Management**: Intelligent management of conversation context
- 📚 **Knowledge Base**: Local vector database for persistent information storage

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

### Context Management
The Context Management feature allows you to optimize token usage and maintain important information in long conversations:

1. **Pin Important Messages**:
   ```
   /pin 5
   ```
   This pins message #5 to ensure it stays in context even as the conversation grows.

2. **Exclude Irrelevant Messages**:
   ```
   /exclude 3
   ```
   This excludes message #3 from the context, saving tokens for more relevant information.

3. **Summarize Conversations**:
   ```
   /summarize
   ```
   This creates a concise summary of the conversation to save tokens while maintaining context.

4. **View Context Status**:
   ```
   /context
   ```
   Shows the current status of your context management, including pinned and excluded messages.

5. **Check Token Usage**:
   ```
   /tokens
   ```
   Displays detailed token usage information for each message.

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
   - Excel Spreadsheets (.xlsx, .xls)
   - PDF Files (.pdf)
   - Text Files (.txt, .md)
   - Code Files (.py, .js, .html, etc.)

2. **Drag & Drop**:
   - Press Ctrl+V to toggle drag & drop mode
   - Drag a document into the terminal
   - The model will analyze the document content

3. **File Creation**:
   - Create files directly from the chat using the `/create` command
   - Standard syntax: `/create [filename] [content]`
   - Natural language syntax: `/create a haiku about nature and save to nature.txt`
   - Example: `/create data.csv "Name,Age,City\nJohn,30,New York\nJane,25,Boston"`
   - Supported formats: TXT, CSV, DOC/DOCX, XLS/XLSX, PDF

### Context Management
The Context Management feature allows you to optimize token usage and maintain important information in long conversations:

1. **Pin Important Messages**:
   ```
   /pin 5
   ```
   This pins message #5 to ensure it stays in context even as the conversation grows.

2. **Exclude Irrelevant Messages**:
   ```
   /exclude 3
   ```
   This excludes message #3 from the context, saving tokens for more relevant information.

3. **Summarize Conversations**:
   ```
   /summarize
   ```
   This creates a concise summary of the conversation to save tokens while maintaining context.

4. **View Context Status**:
   ```
   /context
   ```
   Shows the current status of your context management, including pinned and excluded messages.

5. **Check Token Usage**:
   ```
   /tokens
   ```
   Displays detailed token usage information for each message.

### Knowledge Base
Store and retrieve information using a local vector database:

1. **Features**:
   - Persistent storage across sessions
   - Semantic search for relevant information
   - Automatic integration with chat context
   - Vector embeddings for similarity matching

2. **Usage**:
   - Add important information with `/kb add [text]`
   - Search the knowledge base with `/kb search [query]`
   - Enable/disable with `/kb toggle`
   - View status with `/kb status`

3. **Benefits**:
   - Remember important facts between sessions
   - Build a personalized knowledge repository
   - Automatically enhance responses with relevant context
   - Reduce repetitive questions

4. **Adding Documents**:
   - Drag & drop documents directly into the chat
   - Choose to add them to the knowledge base when prompted
   - Documents are automatically chunked for optimal storage
   - Search across all documents with `/kb search [query]`

## Supported File Formats

### Documents
- 📝 Word Documents (.docx, .doc)
- 📊 Excel Spreadsheets (.xlsx, .xls)
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
- Use `/pin` to keep important context in long conversations
- Use `/summarize` to condense long conversations while maintaining context
- Use the knowledge base to store and retrieve important information across sessions
- Add documents to your knowledge base via drag & drop for persistent access to their content

## Context Management Commands
- `/pin [message_number]` - Pin a message to keep it in context
- `/unpin [message_number]` - Unpin a previously pinned message
- `/exclude [message_number]` - Exclude a message from context
- `/include [message_number]` - Include a previously excluded message
- `/summarize` - Summarize the conversation to save tokens
- `/context` - Show current context management status
- `/tokens` - Show token usage information
- `/help` - Show context management help

## Knowledge Base Commands
- `/kb status` - Show knowledge base status and statistics
- `/kb add [text]` - Add text to your knowledge base
- `/kb search [query]` - Search your knowledge base for relevant information
- `/kb toggle` - Enable or disable knowledge base integration

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
MIT License - See LICENSE file for details
